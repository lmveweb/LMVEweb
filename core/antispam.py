"""Defensas anti-spam del formulario de Contacto, en capas independientes:

1. Honeypot: un campo invisible para una persona real que un bot
   genérico sí rellena porque no distingue qué es visible.
2. Marca de tiempo firmada: un formulario real tarda un mínimo de
   segundos en llenarse; un bot lo envía casi al instante de cargar
   la página.
3. Cloudflare Turnstile: desafío de verificación humana de terceros,
   capa aparte porque requiere red y puede fallar por causas ajenas
   al remitente (ver verificar_turnstile).

Las dos primeras no dependen de nada externo ni de JavaScript, así que
siguen funcionando igual si Turnstile no está configurado o el widget
no llegó a cargar.
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request

from django.core.signing import BadSignature, Signer

logger = logging.getLogger(__name__)

HONEYPOT_FIELD = 'telefono_contacto'

# Pública (no un detalle de implementación) porque los tests fabrican
# tokens directamente con este salt para simular envíos con distintos
# tiempos transcurridos sin depender de sleep() real.
SALT_MARCA_TIEMPO = 'core.antispam.marca_tiempo'
SEGUNDOS_MINIMOS = 3
SEGUNDOS_MAXIMOS = 3600  # pasado esto, se pide recargar en vez de sospechar bot

TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def generar_marca_tiempo():
    """Momento de carga del formulario, firmado para que no se pueda
    simplemente fabricar un valor con un delay artificial.

    Usa Signer (no TimestampSigner/signing.dumps): ese trae su propio
    reloj interno con la hora real de la firma, que no sirve acá porque
    lo que hay que comparar es CUÁNDO SE CARGÓ el formulario contra
    cuándo llegó el POST — dos momentos distintos, ninguno de los dos
    "ahora". Con Signer, el único reloj es el time.time() que se firma
    a mano abajo, y las dos comparaciones (mínimo y máximo) se hacen
    contra ese mismo valor.
    """
    return Signer(salt=SALT_MARCA_TIEMPO).sign_object(time.time())


def es_envio_humano_por_tiempo(valor):
    """True/False si el tiempo transcurrido desde que se cargó el
    formulario parece humano o de bot. None si el valor es inválido o
    superó SEGUNDOS_MAXIMOS (formulario viejo, no necesariamente un bot
    — se le pide a la persona que recargue en vez de rechazarla)."""
    try:
        creado = Signer(salt=SALT_MARCA_TIEMPO).unsign_object(valor)
    except BadSignature:
        return None
    transcurrido = time.time() - creado
    if transcurrido > SEGUNDOS_MAXIMOS:
        return None
    return transcurrido >= SEGUNDOS_MINIMOS


def verificar_turnstile(token, ip, secret_key, timeout=5):
    """Consulta a Cloudflare si el token del widget es válido.

    Si Cloudflare no responde (caído, timeout, sin red), se deja pasar
    el mensaje en vez de bloquearlo: las otras dos capas (honeypot,
    tiempo) y el rate limiting siguen en pie, y no tiene sentido que
    alguien que de verdad quiere escribirle a la Liga se quede sin
    poder hacerlo por un problema de un tercero que no es suyo.
    """
    if not token:
        return False

    datos = urllib.parse.urlencode({
        'secret': secret_key,
        'response': token,
        'remoteip': ip or '',
    }).encode('ascii')

    try:
        with urllib.request.urlopen(TURNSTILE_VERIFY_URL, data=datos, timeout=timeout) as resp:
            resultado = json.loads(resp.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        logger.exception('No se pudo verificar Turnstile; se deja pasar el mensaje')
        return True

    return bool(resultado.get('success'))
