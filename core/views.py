import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods, require_safe
from django_ratelimit.decorators import ratelimit

from .antispam import (
    HONEYPOT_FIELD,
    es_envio_humano_por_tiempo,
    generar_marca_tiempo,
    verificar_turnstile,
)
from .contenido import COLEGIOS, FOTOS_MULTIMEDIA, evento_vigente
from .forms import ContactoForm
from .ip import clave_ratelimit, ip_cliente
from .models import FotoNoticia, Noticia
from .seo import jsonld_home, jsonld_noticia, seo_noticia
from .templatetags.noticias import cuerpo_noticia

logger = logging.getLogger(__name__)

# Las vistas que solo renderizan una plantilla fija (Historia, Sobre,
# Equipo, Privacidad) son TemplateView directo en core/urls.py.


@require_safe
def home(request):
    evento = evento_vigente()
    return render(request, 'core/home.html', {
        'colegios': COLEGIOS,
        'evento': evento,
        'jsonld': jsonld_home(evento),
        'noticias': Noticia.objects.publicadas().prefetch_related('fotos')[:NOTICIAS_EN_PORTADA],
    })


@require_safe
def archivo(request):
    return render(request, 'core/archivo.html', {'fotos': FOTOS_MULTIMEDIA})


# ---------------------------------------------------------------------
# Noticias (las publica la Liga desde el admin, ver core/models.py)
# ---------------------------------------------------------------------

NOTICIAS_EN_PORTADA = 3
NOTICIAS_POR_PAGINA = 12
UN_DIA = 60 * 60 * 24


def _puede_ver_borradores(request):
    """Quien entró al panel ve también las noticias sin publicar: es la
    vista previa antes de marcar "Publicada". "Entró al panel" incluye
    el código de acceso: una sesión con la contraseña sola no basta, igual
    que para el panel mismo (LmveAdminSite.has_permission)."""
    user = request.user
    return user.is_authenticated and user.is_staff and user.is_active and user.is_verified()


@require_safe
def noticias(request):
    pagina = Paginator(
        Noticia.objects.publicadas().prefetch_related('fotos'), NOTICIAS_POR_PAGINA,
    ).get_page(request.GET.get('pagina'))
    return render(request, 'core/noticias.html', {'pagina': pagina})


@require_safe
def noticia(request, slug):
    nota = get_object_or_404(Noticia.objects.prefetch_related('fotos'), slug=slug)
    if not nota.publicada and not _puede_ver_borradores(request):
        raise Http404
    fotos = list(nota.fotos.all())
    cuerpo_html = cuerpo_noticia(nota.cuerpo)
    respuesta = render(request, 'core/noticia.html', {
        'noticia': nota,
        'cuerpo_html': cuerpo_html,
        # El script de Instagram se carga solo si la noticia incrusta
        # alguna publicación (ver core/templatetags/noticias.py).
        'tiene_instagram': 'class="instagram-media"' in cuerpo_html,
        'portada': fotos[0] if fotos else None,
        'galeria': fotos[1:],
        'jsonld': jsonld_noticia(nota) if nota.publicada else None,
        # Pisa lo que entrega el context processor para el resto de las
        # vistas (ver core/seo.py): acá los metadatos salen de la noticia.
        **seo_noticia(nota),
    })
    if not nota.publicada:
        respuesta['Cache-Control'] = 'private, no-store'
    return respuesta


def _imagen(contenido, tipo, publicada, cache):
    respuesta = HttpResponse(bytes(contenido), content_type=tipo)
    respuesta['Cache-Control'] = cache if publicada else 'private, no-store'
    return respuesta


@require_safe
def noticia_foto(request, pk, version, tamano):
    """Sirve una foto desde la base de datos (ver FotoNoticia).

    La dirección lleva la versión de la imagen: si la foto cambia, cambia
    la dirección, así que el navegador puede guardarla por un año sin
    volver a pedirla. Las fotos de un borrador solo las ve quien entró
    al panel, igual que el borrador mismo.
    """
    if tamano == 'o':
        # La portada sin recortar, para el editor del panel. Nunca
        # pública: puede mostrar partes de la foto que se recortaron a
        # propósito.
        if not _puede_ver_borradores(request):
            raise Http404
        fila = FotoNoticia.objects.filter(pk=pk, version=version).values_list('original', 'grande').first()
        if fila is None:
            raise Http404
        return _imagen(fila[0] or fila[1], 'image/webp', False, None)

    campo = {'m': 'miniatura', 'g': 'grande'}.get(tamano)
    if campo is None:
        raise Http404
    fila = (FotoNoticia.objects.filter(pk=pk, version=version)
            .values_list(campo, 'noticia__publicada').first())
    if fila is None:
        raise Http404
    contenido, publicada = fila
    if not publicada and not _puede_ver_borradores(request):
        raise Http404
    # Un día y no un año, aunque la dirección cambie con cada versión: son
    # fotos de menores. Si alguien pide sacar una, despublicar o borrar la
    # noticia la saca de los navegadores y de Cloudflare a más tardar al
    # día siguiente (al tiro, si además se purga la caché en Cloudflare).
    return _imagen(contenido, 'image/webp', publicada, f'public, max-age={UN_DIA}')


@require_safe
def noticia_social(request, slug):
    """La imagen de la vista previa al compartir el link (og:image)."""
    fila = Noticia.objects.filter(slug=slug).values_list('imagen_social', 'publicada').first()
    if fila is None or fila[0] is None:
        raise Http404
    contenido, publicada = fila
    if not publicada and not _puede_ver_borradores(request):
        raise Http404
    return _imagen(contenido, 'image/jpeg', publicada, f'public, max-age={UN_DIA}')


# require_safe (GET y HEAD), no require_GET: varios rastreadores y
# herramientas de SEO consultan robots.txt con HEAD antes de pedirlo.
@require_safe
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    lineas = [
        'User-agent: *',
        'Allow: /',
        '',
        f'Sitemap: {settings.SITE_URL}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lineas) + '\n', content_type='text/plain; charset=utf-8')


def _error(mensajes, status=400):
    return JsonResponse({'ok': False, 'errores': mensajes}, status=status)


def _origen(request):
    """Para los registros: la IP del visitante y, aparte, la de la
    conexión. Si las dos coinciden y parecen internas (10.x), el
    encabezado de DJANGO_CLIENT_IP_HEADER no está llegando: ver
    core/ip.py."""
    return f'IP {ip_cliente(request)}, conexión {request.META.get("REMOTE_ADDR")}'


def _filtrar_bots(request):
    """Honeypot y marca de tiempo (ver core/antispam.py). Devuelve la
    respuesta a dar si el envío se bloquea, o None si pasa.

    A un bot que dispara cualquiera de las dos se le finge un éxito (200
    "ok") en vez de un error. Un error le confirmaría que hay algo que
    evadir y lo empujaría a intentarlo de nuevo distinto; un falso éxito
    lo deja creyendo que ya funcionó. Ninguna persona real cae en
    ninguna de las dos: el campo es invisible y 3 segundos es menos de
    lo que toma leer el primer campo del formulario.
    """
    if request.POST.get(HONEYPOT_FIELD, '').strip():
        logger.warning('Contacto bloqueado por honeypot (%s)', _origen(request))
        return JsonResponse({'ok': True})

    segun_tiempo = es_envio_humano_por_tiempo(request.POST.get('marca_tiempo', ''))
    if segun_tiempo is None:
        # Formulario abierto hace más de una hora (o marca adulterada):
        # a diferencia de arriba, esto sí le puede pasar a una persona
        # real que dejó la pestaña abierta, así que se le pide recargar
        # en vez de tratarla como bot.
        return _error(['El formulario expiró. Recarga la página e intenta de nuevo.'])
    if not segun_tiempo:
        logger.warning('Contacto bloqueado por envío demasiado rápido (%s)', _origen(request))
        return JsonResponse({'ok': True})

    return None


def _avisar_por_correo(mensaje):
    """El mensaje ya quedó guardado (y visible en el admin) aunque el
    correo de aviso falle, así que un problema de envío no hace perder
    el contacto: solo se registra en el log."""
    if not settings.CONTACTO_DESTINATARIO:
        return

    cuerpo = (
        f'Nombre y apellido: {mensaje.nombre}\n'
        f'Institución: {mensaje.institucion or "(no indicada)"}\n'
        f'Correo: {mensaje.email}\n\n'
        f'Mensaje:\n{mensaje.mensaje}'
    )
    try:
        EmailMessage(
            subject=f'[LMVE] Nuevo mensaje de contacto: {mensaje.nombre}',
            body=cuerpo,
            to=[settings.CONTACTO_DESTINATARIO],
            reply_to=[mensaje.email],
        ).send(fail_silently=False)
    except Exception:
        logger.exception('No se pudo enviar el correo de aviso del formulario de Contacto')


@require_http_methods(['GET', 'HEAD', 'POST'])
@ratelimit(key=clave_ratelimit, rate='5/m', method='POST', block=False)
def contacto(request):
    if request.method != 'POST':
        return render(request, 'core/contacto.html', {
            'form': ContactoForm(),
            'marca_tiempo': generar_marca_tiempo(),
            'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        })

    if getattr(request, 'limited', False):
        logger.warning('Contacto frenado por límite de intentos (%s)', _origen(request))
        return _error(['Demasiados intentos. Espera un minuto e intenta de nuevo.'], status=429)

    bloqueo = _filtrar_bots(request)
    if bloqueo is not None:
        return bloqueo

    form = ContactoForm(request.POST)
    if not form.is_valid():
        return _error(form.lista_errores())

    # Turnstile va DESPUÉS de validar los campos: cada token sirve para
    # una sola verificación, así que si se consultara antes, una persona
    # que solo se equivocó en el correo gastaría su token y el reintento
    # fallaría con "no pudimos verificar que eres una persona".
    #
    # A diferencia del honeypot y el tiempo, un fallo acá sí puede
    # tocarle a una persona real (JS bloqueado, extensión de privacidad,
    # adblocker), así que se devuelve un error real invitando a
    # reintentar. Sin TURNSTILE_SECRET_KEY, esta capa no corre.
    if settings.TURNSTILE_SECRET_KEY:
        token = request.POST.get('cf-turnstile-response', '')
        if not verificar_turnstile(token, ip_cliente(request), settings.TURNSTILE_SECRET_KEY):
            return _error(['No pudimos verificar que eres una persona. Recarga la página e intenta de nuevo.'])

    _avisar_por_correo(form.save())
    logger.info('Contacto recibido (%s)', _origen(request))
    return JsonResponse({'ok': True})
