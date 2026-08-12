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
MAX_EMPRESA = MensajePatrocinio._meta.get_field('empresa').max_length
MAX_CONTACTO = MensajePatrocinio._meta.get_field('contacto').max_length
MAX_EMAIL = MensajePatrocinio._meta.get_field('email').max_length


def home(request):
    return render(request, 'core/home.html')

def proyecto(request):
    return render(request, 'core/proyecto.html')

def impacto(request):
    return render(request, 'core/impacto.html')

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

        empresa = request.POST.get('empresa', '').strip()
        contacto_nombre = request.POST.get('contacto', '').strip()
        email = request.POST.get('email', '').strip()
        interes = request.POST.get('interes', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()

        errores = []
        if not empresa:
            errores.append('Falta el nombre de la empresa o marca.')
        elif len(empresa) > MAX_EMPRESA:
            errores.append(f'El nombre de la empresa o marca no puede superar los {MAX_EMPRESA} caracteres.')
        if not contacto_nombre:
            errores.append('Falta la persona de contacto.')
        elif len(contacto_nombre) > MAX_CONTACTO:
            errores.append(f'El nombre de la persona de contacto no puede superar los {MAX_CONTACTO} caracteres.')
        if not email:
            errores.append('Falta el correo electrónico.')
        elif len(email) > MAX_EMAIL:
            errores.append(f'El correo electrónico no puede superar los {MAX_EMAIL} caracteres.')
        else:
            try:
                validate_email(email)
            except ValidationError:
                errores.append('El correo electrónico no es válido.')
        if interes not in MensajePatrocinio.NivelInteres.values:
            errores.append('El nivel de interés no es válido.')

        if errores:
            return JsonResponse({'ok': False, 'errores': errores}, status=400)

        MensajePatrocinio.objects.create(
            empresa=empresa,
            contacto=contacto_nombre,
            email=email,
            interes=interes,
            mensaje=mensaje,
        )

        # El mensaje ya quedó guardado (y visible en /admin/) aunque el
        # correo de aviso falle, así que un problema de envío no hace
        # perder el contacto: solo se registra en el log.
        if settings.CONTACTO_DESTINATARIO:
            interes_legible = dict(MensajePatrocinio.NivelInteres.choices).get(interes, interes)
            cuerpo = (
                f'Empresa o marca: {empresa}\n'
                f'Persona de contacto: {contacto_nombre}\n'
                f'Correo: {email}\n'
                f'Nivel de interés: {interes_legible}\n\n'
                f'Mensaje:\n{mensaje or "(sin mensaje adicional)"}'
            )
            try:
                EmailMessage(
                    subject=f'[LMVE] Nuevo contacto de patrocinio: {empresa}',
                    body=cuerpo,
                    to=[settings.CONTACTO_DESTINATARIO],
                    reply_to=[email],
                ).send(fail_silently=False)
            except Exception:
                logger.exception('No se pudo enviar el correo de aviso del formulario de Contacto')

        return JsonResponse({'ok': True})

    return render(request, 'core/contacto.html')