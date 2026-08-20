import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit

from .models import MensajePatrocinio

logger = logging.getLogger(__name__)

# Mismos límites que el modelo (ver core/models.py): se validan acá
# también porque hoy solo los aplica el "maxlength" del HTML, y un POST
# directo (sin pasar por el formulario) los ignora sin esfuerzo. Con
# SQLite ese límite ni se aplica a nivel de motor; con Postgres en
# producción, un valor más largo tiraría un DataError no controlado.
MAX_NOMBRE = MensajePatrocinio._meta.get_field('nombre').max_length
MAX_INSTITUCION = MensajePatrocinio._meta.get_field('institucion').max_length
MAX_EMAIL = MensajePatrocinio._meta.get_field('email').max_length


# Colegios que compiten en la Liga, para el carrusel de Inicio. Lista en
# Python (no en el template) por la misma razón que FOTOS_MULTIMEDIA:
# sumar o sacar un colegio es editar una línea acá, sin tocar el HTML.
COLEGIOS = [
    {'src': 'core/img/colegios/colegio-aleman-santiago.png', 'alt': 'Colegio Alemán Santiago'},
    {'src': 'core/img/colegios/colegio-alicante-del-valle.png', 'alt': 'Colegio Alicante del Valle'},
    {'src': 'core/img/colegios/colegio-andree-english-school.png', 'alt': 'Colegio Andrée English School'},
    {'src': 'core/img/colegios/colegio-british-royal-school.png', 'alt': 'Colegio British Royal School'},
    {'src': 'core/img/colegios/colegio-carampangue.png', 'alt': 'Colegio Carampangue'},
    {'src': 'core/img/colegios/colegio-colonial-de-pirque.png', 'alt': 'Colegio Colonial de Pirque'},
    {'src': 'core/img/colegios/colegio-cumbres.png', 'alt': 'Colegio Cumbres'},
    {'src': 'core/img/colegios/colegio-epullay-montessori.png', 'alt': 'Colegio Epullay Montessori'},
    {'src': 'core/img/colegios/colegio-hispano-americano.png', 'alt': 'Colegio Hispano Americano'},
    {'src': 'core/img/colegios/colegio-institucion-teresiana.png', 'alt': 'Colegio Institución Teresiana'},
    {'src': 'core/img/colegios/colegio-instituto-alonso-de-ercilla.png', 'alt': 'Colegio Instituto Alonso de Ercilla'},
    {'src': 'core/img/colegios/colegio-instituto-santa-maria.png', 'alt': 'Colegio Instituto Santa María'},
    {'src': 'core/img/colegios/colegio-juanita-de-los-andes.png', 'alt': 'Colegio Juanita de los Andes'},
    {'src': 'core/img/colegios/colegio-la-girouette.png', 'alt': 'Colegio La Girouette'},
    {'src': 'core/img/colegios/colegio-la-maissonette.png', 'alt': 'Colegio La Maissonette'},
    {'src': 'core/img/colegios/colegio-lincoln-international-chicureo.png', 'alt': 'Colegio Lincoln International (Chicureo)'},
    {'src': 'core/img/colegios/colegio-lincoln-lo-barnechea.png', 'alt': 'Colegio Lincoln Lo Barnechea'},
    {'src': 'core/img/colegios/colegio-marcelino-champagnat.png', 'alt': 'Colegio Marcelino Champagnat'},
    {'src': 'core/img/colegios/colegio-mariano-de-schoenstatt.png', 'alt': 'Colegio Mariano de Schoenstatt'},
    {'src': 'core/img/colegios/colegio-maria-inmaculada.png', 'alt': 'Colegio María Inmaculada'},
    {'src': 'core/img/colegios/colegio-mayor-penalolen.png', 'alt': 'Colegio Mayor Peñalolén'},
    {'src': 'core/img/colegios/colegio-mayor-tobalaba.png', 'alt': 'Colegio Mayor Tobalaba'},
    {'src': 'core/img/colegios/colegio-monte-tabor-y-nazaret.png', 'alt': 'Colegio Monte Tabor y Nazaret'},
    {'src': 'core/img/colegios/colegio-notre-dame.png', 'alt': 'Colegio Notre Dame'},
    {'src': 'core/img/colegios/colegio-pedro-de-valdivia-penalolen.png', 'alt': 'Colegio Pedro de Valdivia Peñalolén'},
    {'src': 'core/img/colegios/colegio-sscc-providencia.png', 'alt': 'Colegio SSCC Providencia'},
    {'src': 'core/img/colegios/colegio-sagrado-corazon-talagante.png', 'alt': 'Colegio Sagrado Corazón Talagante'},
    {'src': 'core/img/colegios/colegio-san-felipe-diacono.png', 'alt': 'Colegio San Felipe Diácono'},
    {'src': 'core/img/colegios/colegio-san-ignacio-alonso-ovalle.png', 'alt': 'Colegio San Ignacio Alonso Ovalle'},
    {'src': 'core/img/colegios/colegio-san-ignacio-el-bosque.png', 'alt': 'Colegio San Ignacio el Bosque'},
    {'src': 'core/img/colegios/colegio-san-jose-de-chicureo.png', 'alt': 'Colegio San José de Chicureo'},
    {'src': 'core/img/colegios/colegio-san-nicolas-diacono.png', 'alt': 'Colegio San Nicolás Diacono'},
    {'src': 'core/img/colegios/colegio-san-pedro-nolasco.png', 'alt': 'Colegio San Pedro Nolasco'},
    {'src': 'core/img/colegios/colegio-santa-cruz-de-chicureo.png', 'alt': 'Colegio Santa Cruz de Chicureo'},
    {'src': 'core/img/colegios/colegio-santa-maria-lo-canas.png', 'alt': 'Colegio Santa María Lo Cañas'},
    {'src': 'core/img/colegios/colegio-scuola-italiana.png', 'alt': 'Colegio Scuola Italiana'},
    {'src': 'core/img/colegios/colegio-sek-internacional-chile.png', 'alt': 'Colegio Sek Internacional Chile'},
    {'src': 'core/img/colegios/colegio-suizo-de-santiago.png', 'alt': 'Colegio Suizo de Santiago'},
    {'src': 'core/img/colegios/colegio-the-english-institute.png', 'alt': 'Colegio The English Institute'},
    {'src': 'core/img/colegios/colegio-the-southern-cross-school.png', 'alt': 'Colegio The Southern Cross School'},
    {'src': 'core/img/colegios/colegio-thomas-morus.png', 'alt': 'Colegio Thomas Morus'},
    {'src': 'core/img/colegios/liceo-alianza-francesa.png', 'alt': 'Liceo Alianza Francesa'},
    {'src': 'core/img/colegios/liceo-camilo-ortuzar-montt.png', 'alt': 'Liceo Camilo Ortúzar Montt'},
    {'src': 'core/img/colegios/liceo-manuel-de-salas.png', 'alt': 'Liceo Manuel de Salas'},
    {'src': 'core/img/colegios/liceo-nacional-maipu.png', 'alt': 'Liceo Nacional Maipú'},
    {'src': 'core/img/colegios/liceo-salesiano-manuel-arriaran-barros.jpeg', 'alt': 'Liceo Salesiano Manuel Arriaran Barros'},
    {'src': 'core/img/colegios/the-grange-school.png', 'alt': 'The Grange School'},
]


def home(request):
    return render(request, 'core/home.html', {'colegios': COLEGIOS})

def proyecto(request):
    return render(request, 'core/proyecto.html')

def staff(request):
    return render(request, 'core/staff.html')

def privacidad(request):
    return render(request, 'core/privacidad.html')

# Fotos de la galería de Multimedia. Lista en Python (no en el
# template) para que sumar fotos nuevas sea agregar una línea acá, sin
# tocar HTML.
FOTOS_MULTIMEDIA = [
    {'src': 'core/img/fotos/galeria-1.jpg', 'alt': 'Armado en zona de red durante un partido de la Liga'},
    {'src': 'core/img/fotos/galeria-2.jpg', 'alt': 'Bloqueo en la red durante un partido de la Liga'},
    {'src': 'core/img/fotos/galeria-3.jpg', 'alt': 'Saque de salto durante un partido de la Liga'},
    {'src': 'core/img/fotos/impacto-reconocimiento.jpg', 'alt': 'Ceremonia de reconocimiento a colaboradores de la Liga'},
    {'src': 'core/img/fotos/galeria-4.jpg', 'alt': 'Remate durante una jornada de competencia'},
    {'src': 'core/img/fotos/archivo-hoy-2.jpg', 'alt': 'Disputa de balón sobre la red'},
    {'src': 'core/img/fotos/archivo-hoy-5.jpg', 'alt': 'Remate frente al bloqueo rival'},
    {'src': 'core/img/fotos/archivo-jornada-2.jpg', 'alt': 'Equipos formados en cancha durante una ceremonia'},
    {'src': 'core/img/fotos/archivo-jornada-3.jpg', 'alt': 'Equipos posando junto a la red al término de una jornada'},
    {'src': 'core/img/fotos/archivo-jornada-1.jpg', 'alt': 'Presentación de los colegios participantes'},
    {'src': 'core/img/fotos/impacto-banner-sponsor.jpg', 'alt': 'Plantel completo en un recinto de la Liga'},
    {'src': 'core/img/fotos/archivo-hoy-1.jpg', 'alt': 'Trofeos y balones preparados para la premiación'},
    {'src': 'core/img/fotos/historia-1987.jpg', 'alt': 'Equipo de la Liga a fines de los años 80'},
    {'src': 'core/img/fotos/archivo-80s-2.jpg', 'alt': 'Equipo junto a su profesor, década de 1980'},
    {'src': 'core/img/fotos/archivo-90s-seleccion.jpg', 'alt': 'Selección de la Liga, 1990'},
]

# Tanda de fotos recientes (jornadas 2026) sumada más adelante: sin
# contexto de fecha/colegio/categoría por foto todavía, así que llevan
# alt genérico. Cuando haya esa información, lo ideal es reemplazar
# este bloque por entradas explícitas como las de arriba.
FOTOS_MULTIMEDIA += [
    {'src': f'core/img/fotos/galeria-{i}.jpg', 'alt': 'Fotografía de un partido de la Liga'}
    for i in range(5, 58)
]


def archivo(request):
    return render(request, 'core/archivo.html', {'fotos': FOTOS_MULTIMEDIA})


def sobre(request):
    return render(request, 'core/sobre.html')


@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def contacto(request):
    if request.method == 'POST':
        if getattr(request, 'limited', False):
            return JsonResponse(
                {'ok': False, 'errores': ['Demasiados intentos. Espera un minuto e intenta de nuevo.']},
                status=429,
            )

        nombre = request.POST.get('nombre', '').strip()
        institucion = request.POST.get('institucion', '').strip()
        email = request.POST.get('email', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        acepta_politica = request.POST.get('acepta_politica', '').strip()

        errores = []
        if not nombre:
            errores.append('Falta el nombre y apellido.')
        elif len(nombre) > MAX_NOMBRE:
            errores.append(f'El nombre y apellido no puede superar los {MAX_NOMBRE} caracteres.')
        if len(institucion) > MAX_INSTITUCION:
            errores.append(f'El nombre de la institución no puede superar los {MAX_INSTITUCION} caracteres.')
        if not email:
            errores.append('Falta el correo electrónico.')
        elif len(email) > MAX_EMAIL:
            errores.append(f'El correo electrónico no puede superar los {MAX_EMAIL} caracteres.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errores.append('El correo electrónico no es válido.')
        if not mensaje:
            errores.append('Falta el mensaje.')
        # Igual que el resto: el navegador ya lo exige con "required", pero
        # un POST directo lo puede saltar sin esfuerzo.
        if not acepta_politica:
            errores.append('Debes aceptar la Política de Privacidad para continuar.')

        if errores:
            return JsonResponse({'ok': False, 'errores': errores}, status=400)

        MensajePatrocinio.objects.create(
            nombre=nombre,
            institucion=institucion,
            email=email,
            mensaje=mensaje,
        )

        # El mensaje ya quedó guardado (y visible en /admin/) aunque el
        # correo de aviso falle, así que un problema de envío no hace
        # perder el contacto: solo se registra en el log.
        if settings.CONTACTO_DESTINATARIO:
            cuerpo = (
                f'Nombre y apellido: {nombre}\n'
                f'Institución: {institucion or "(no indicada)"}\n'
                f'Correo: {email}\n\n'
                f'Mensaje:\n{mensaje}'
            )
            try:
                EmailMessage(
                    subject=f'[LMVE] Nuevo mensaje de contacto: {nombre}',
                    body=cuerpo,
                    to=[settings.CONTACTO_DESTINATARIO],
                    reply_to=[email],
                ).send(fail_silently=False)
            except Exception:
                logger.exception('No se pudo enviar el correo de aviso del formulario de Contacto')

        return JsonResponse({'ok': True})

    return render(request, 'core/contacto.html')