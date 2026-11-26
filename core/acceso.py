"""Ingreso al panel en dos pasos.

Paso 1: usuario y contraseña. Si están bien, el código de acceso sale
solo al correo de la persona. Paso 2: el código, sin volver a escribir
la contraseña.

Entre un paso y otro NO hay sesión iniciada: en la sesión solo queda
anotado quién pasó el primer paso (PENDIENTE), por 10 minutos. Recién
con el código correcto se llama a login(), y con el dispositivo ya
verificado, que es lo que exige LmveAdminSite.has_permission.

"Recordar este computador" deja una cookie firmada que, durante 30 días,
evita el código en ese navegador (la contraseña se pide siempre). Lleva
una huella de la contraseña: al cambiarla, todos los computadores
recordados de esa persona dejan de servir.
"""

import logging
import secrets
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.contrib.auth import login as auth_login
from django.core import signing
from django.db import transaction
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.crypto import constant_time_compare
from django.utils.http import url_has_allowed_host_and_scheme
from django_otp.plugins.otp_email.models import EmailDevice

from .ip import ip_cliente

logger = logging.getLogger(__name__)

GRUPO_EDITORES = 'Editores'

PENDIENTE = 'acceso_pendiente'
SEGUNDOS_PENDIENTE = 10 * 60

COOKIE_RECORDAR = 'lmve_equipo'
SEGUNDOS_RECORDAR = 30 * 24 * 60 * 60
SALT_RECORDAR = 'core.acceso.recordar'

# Sin 0/o, 1/l/i: la clave temporal se dicta por teléfono o videollamada.
LETRAS_CLAVE = 'abcdefghjkmnpqrstuvwxyz'
DIGITOS_CLAVE = '23456789'


def dispositivo_de(user):
    """El código por correo activado para esta persona, o None."""
    return EmailDevice.objects.filter(user=user, confirmed=True).order_by('pk').first()


def activar_codigo_por_correo(user, email=None):
    """Deja a la persona con el código por correo activado. Sin `email`,
    los códigos van al correo de su ficha (y lo siguen si se cambia)."""
    defaults = {'confirmed': True}
    if email is not None:
        defaults['email'] = email
    return EmailDevice.objects.update_or_create(user=user, name='default', defaults=defaults)


def clave_temporal():
    """Clave al azar, fácil de dictar: tres grupos de cuatro, cada uno
    con letras y un número (unos 55 bits)."""
    grupos = []
    for _ in range(3):
        grupo = [secrets.choice(LETRAS_CLAVE) for _ in range(3)] + [secrets.choice(DIGITOS_CLAVE)]
        secrets.SystemRandom().shuffle(grupo)
        grupos.append(''.join(grupo))
    return '-'.join(grupos)


def correo_disimulado(device):
    """ma•••@gmail.com: alcanza para saber a qué casilla ir a mirar, sin
    mostrar el correo completo a quien esté mirando la pantalla."""
    usuario, _, dominio = (device.email or device.user.email or '').partition('@')
    return f'{usuario[:2]}•••@{dominio}' if dominio else ''


# ---------------------------------------------------------------------
# Recordar este computador
# ---------------------------------------------------------------------

def _valor_recordar(user, device):
    return signing.dumps(
        {'u': user.pk, 'd': device.pk, 'h': user.get_session_auth_hash()}, salt=SALT_RECORDAR,
    )


def _equipo_recordado(request, user, device):
    valor = request.COOKIES.get(COOKIE_RECORDAR)
    if not valor:
        return False
    try:
        datos = signing.loads(valor, salt=SALT_RECORDAR, max_age=SEGUNDOS_RECORDAR)
    except signing.BadSignature:
        return False
    return (
        isinstance(datos, dict)
        and datos.get('u') == user.pk
        and datos.get('d') == device.pk
        and constant_time_compare(str(datos.get('h', '')), user.get_session_auth_hash())
    )


# ---------------------------------------------------------------------
# Entre el paso 1 y el paso 2
# ---------------------------------------------------------------------

def _anotar_pendiente(request, user, device, destino):
    request.session[PENDIENTE] = {
        'u': user.pk, 'd': device.pk, 'h': user.get_session_auth_hash(),
        'b': user.backend, 'desde': time.time(), 'destino': destino,
    }


def _pendiente(request):
    """(usuario, dispositivo, datos) de quien ya pasó la contraseña, o
    (None, None, None). Se vuelve a comprobar todo en cada petición: la
    cuenta pudo desactivarse, perder el acceso al panel o cambiar su
    contraseña mientras esperaba el código."""
    datos = request.session.get(PENDIENTE)
    if not datos:
        return None, None, None
    user = device = None
    if time.time() - datos.get('desde', 0) <= SEGUNDOS_PENDIENTE:
        user = get_user_model().objects.filter(pk=datos.get('u'), is_active=True, is_staff=True).first()
    if user and constant_time_compare(str(datos.get('h', '')), user.get_session_auth_hash()):
        device = EmailDevice.objects.filter(pk=datos.get('d'), user=user, confirmed=True).first()
    if not device:
        del request.session[PENDIENTE]
        return None, None, None
    return user, device, datos


def _enviar_codigo(request, device):
    """Manda un código nuevo. Devuelve 'enviado', 'espera' (hace menos
    de un minuto se mandó otro, que sigue sirviendo) o 'fallo' (no salió
    el correo; deja el aviso en pantalla)."""
    permitido, _ = device.generate_is_allowed()
    if not permitido:
        return 'espera'
    try:
        device.generate_challenge()
    except Exception:
        logger.exception('No se pudo enviar el código de acceso de %s', device.user.get_username())
        # Sin esto habría que esperar un minuto para reintentar un envío
        # que nunca salió.
        device.cooldown_reset()
        messages.error(request, 'No pudimos enviarte el código. Prueba de nuevo con "Enviar otro código".')
        return 'fallo'
    return 'enviado'


def _entrar(request, user, device, destino, recordar=False):
    # django-otp escucha el login y deja el dispositivo verificado en la
    # sesión a partir de este atributo.
    user.otp_device = device
    auth_login(request, user)
    request.session.pop(PENDIENTE, None)
    logger.info('Ingreso al panel: %s (IP %s, %s)', user.get_username(), ip_cliente(request),
                getattr(request, 'origen_estado', 'origen sin revisar'))
    respuesta = HttpResponseRedirect(destino)
    if recordar:
        respuesta.set_cookie(
            COOKIE_RECORDAR, _valor_recordar(user, device),
            max_age=SEGUNDOS_RECORDAR,
            # Solo viaja a las direcciones del panel.
            path=reverse('admin:index', current_app=request.current_app),
            secure=settings.SESSION_COOKIE_SECURE, httponly=True, samesite='Strict',
        )
    return respuesta


def _destino(request, inicio):
    destino = request.POST.get(REDIRECT_FIELD_NAME) or request.GET.get(REDIRECT_FIELD_NAME) or ''
    seguro = url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure(),
    )
    return destino if seguro else inicio


# ---------------------------------------------------------------------
# La vista (la monta LmveAdminSite.login, con su límite de intentos)
# ---------------------------------------------------------------------

def ingresar(sitio, request, extra_context=None):
    request.current_app = sitio.name
    inicio = reverse('admin:index', current_app=sitio.name)
    aqui = reverse('admin:login', current_app=sitio.name)

    if request.method == 'GET' and sitio.has_permission(request):
        return HttpResponseRedirect(inicio)

    user, device, datos = _pendiente(request)
    form = AdminAuthenticationForm(request)
    error = ''

    if request.method == 'POST':
        paso = request.POST.get('paso', 'clave')

        if paso == 'cancelar':
            request.session.pop(PENDIENTE, None)
            return HttpResponseRedirect(aqui)

        if paso in ('codigo', 'reenviar') and not device:
            messages.error(request, 'Pasó mucho tiempo. Ingresa de nuevo tu usuario y contraseña.')
            return HttpResponseRedirect(aqui)

        if paso == 'reenviar':
            resultado = _enviar_codigo(request, device)
            if resultado == 'enviado':
                messages.success(request, 'Te enviamos un código nuevo.')
            elif resultado == 'espera':
                messages.warning(
                    request,
                    'Ya te enviamos un código hace menos de un minuto. Revisa tu correo, '
                    'también la carpeta de spam.',
                )
            return HttpResponseRedirect(aqui)

        if paso == 'codigo':
            codigo = ''.join(request.POST.get('codigo', '').split())
            with transaction.atomic():
                device = EmailDevice.objects.select_for_update().get(pk=device.pk)
                permitido, _ = device.verify_is_allowed()
                correcto = bool(permitido and codigo and device.verify_token(codigo))
            if correcto:
                user.backend = datos['b']
                return _entrar(
                    request, user, device, datos.get('destino') or inicio,
                    recordar=bool(request.POST.get('recordar')),
                )
            error = (
                'El código no es correcto o ya venció.' if permitido
                else 'Demasiados intentos fallidos. Espera un momento y prueba de nuevo.'
            )

        else:
            # Paso 1. Empezar de nuevo descarta lo que hubiera pendiente.
            request.session.pop(PENDIENTE, None)
            user = device = None
            form = AdminAuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                device = dispositivo_de(user)
                destino = _destino(request, inicio)
                if device is None:
                    user = None
                    form.add_error(None, (
                        'Tu cuenta todavía no tiene activado el código de acceso por correo. '
                        'Pídele a quien administra el sitio que lo active.'
                    ))
                elif _equipo_recordado(request, user, device):
                    return _entrar(request, user, device, destino)
                else:
                    _anotar_pendiente(request, user, device, destino)
                    _enviar_codigo(request, device)
                    return HttpResponseRedirect(aqui)

    contexto = {
        **sitio.each_context(request),
        'title': 'Iniciar sesión',
        'subtitle': None,
        'app_path': request.get_full_path(),
        'form': form,
        'paso_codigo': bool(device),
        'correo': correo_disimulado(device) if device else '',
        'error_codigo': error,
        REDIRECT_FIELD_NAME: _destino(request, ''),
        **(extra_context or {}),
    }
    return TemplateResponse(request, 'core/admin/login.html', contexto)
