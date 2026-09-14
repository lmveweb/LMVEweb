import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods, require_safe
from django_ratelimit.decorators import ratelimit

from .antispam import (
    HONEYPOT_FIELD,
    es_envio_humano_por_tiempo,
    generar_marca_tiempo,
    verificar_turnstile,
)
from .contenido import COLEGIOS, FOTOS_MULTIMEDIA
from .forms import ContactoForm
from .seo import jsonld_home

logger = logging.getLogger(__name__)

# Las vistas que solo renderizan una plantilla fija (Historia, Sobre,
# Equipo, Privacidad) son TemplateView directo en core/urls.py.


@require_safe
def home(request):
    return render(request, 'core/home.html', {'colegios': COLEGIOS, 'jsonld': jsonld_home()})


@require_safe
def archivo(request):
    return render(request, 'core/archivo.html', {'fotos': FOTOS_MULTIMEDIA})


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


def _ip(request):
    return request.META.get('REMOTE_ADDR')


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
        logger.warning('Contacto bloqueado por honeypot (IP %s)', _ip(request))
        return JsonResponse({'ok': True})

    segun_tiempo = es_envio_humano_por_tiempo(request.POST.get('marca_tiempo', ''))
    if segun_tiempo is None:
        # Formulario abierto hace más de una hora (o marca adulterada):
        # a diferencia de arriba, esto sí le puede pasar a una persona
        # real que dejó la pestaña abierta, así que se le pide recargar
        # en vez de tratarla como bot.
        return _error(['El formulario expiró. Recarga la página e intenta de nuevo.'])
    if not segun_tiempo:
        logger.warning('Contacto bloqueado por envío demasiado rápido (IP %s)', _ip(request))
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
@ratelimit(key='ip', rate='5/m', method='POST', block=False)
def contacto(request):
    if request.method != 'POST':
        return render(request, 'core/contacto.html', {
            'form': ContactoForm(),
            'marca_tiempo': generar_marca_tiempo(),
            'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        })

    if getattr(request, 'limited', False):
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
        if not verificar_turnstile(token, _ip(request), settings.TURNSTILE_SECRET_KEY):
            return _error(['No pudimos verificar que eres una persona. Recarga la página e intenta de nuevo.'])

    _avisar_por_correo(form.save())
    return JsonResponse({'ok': True})
