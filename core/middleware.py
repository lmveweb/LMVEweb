"""Origen de las visitas y tope de tamaño de lo que se envía al sitio.

OrigenDelProxyMiddleware va primero en settings.MIDDLEWARE:

- Revisa la clave secreta que Cloudflare agrega a cada visita (una regla
  de "Transform Rules" que pone el encabezado X-Lmve-Origen). Solo
  cuando viene la clave correcta se confía en la IP que entrega
  Cloudflare (ver core/ip.py): a Render se puede llegar directo, sin
  pasar por Cloudflare, y ahí CF-Connecting-IP lo escribe quien quiera.
  Después borra la clave del request, para que no viaje a Sentry junto
  con los demás encabezados si hay un error.
- Manda la dirección que Render le da al sitio (lmveweb.onrender.com) al
  dominio propio, para que haya una sola dirección pública. Esto solo no
  cierra el hueco de arriba: a Render se puede llegar directo también
  pidiendo ligamve.cl. Por eso la clave.

TopeDeSubidaMiddleware va después de la autenticación: antes de que
Django lea el cuerpo de un envío (lo hace la protección CSRF, en
cualquier dirección), rechaza los que declaran un tamaño mayor al que el
sitio necesita. Sin esto, cualquiera puede mandar cientos de MB que el
servidor guarda en disco mientras ocupa uno de sus 4 hilos.
"""

from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.utils.crypto import constant_time_compare

ENCABEZADO_ORIGEN = 'X-Lmve-Origen'
_META_ORIGEN = 'HTTP_' + ENCABEZADO_ORIGEN.upper().replace('-', '_')

MB = 1024 * 1024
# Contacto y el login pesan unos pocos KB.
TOPE_SIN_SESION = 1 * MB
# Una noticia nueva con portada y las 8 fotos de galería, de hasta 10 MB
# cada una (ver core/imagenes.py), más el texto.
TOPE_PANEL = 100 * MB


def estado_origen(clave, recibida, verificado):
    """Qué pasó con la clave, para el registro de ingresos al panel: así
    se ve si la regla de Cloudflare está funcionando. Nunca incluye la
    clave; a lo más su largo, para notar un carácter de más o de menos."""
    if not clave:
        return 'sin clave configurada'
    if verificado:
        return 'clave verificada'
    if not recibida:
        return 'no llegó la clave'
    return f'clave distinta ({len(recibida)} caracteres; se esperaban {len(clave)})'


class OrigenDelProxyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        recibida = request.META.pop(_META_ORIGEN, '').strip()
        clave = settings.PROXY_CLAVE
        request.origen_verificado = bool(clave) and constant_time_compare(recibida, clave)
        request.origen_estado = estado_origen(clave, recibida, request.origen_verificado)

        host = request.META.get('HTTP_HOST', '').split(':')[0].lower()
        if host.endswith('.onrender.com'):
            return HttpResponsePermanentRedirect(settings.SITE_URL + request.get_full_path())
        return self.get_response(request)


class TopeDeSubidaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            largo = int(request.META.get('CONTENT_LENGTH') or 0)
        except ValueError:
            largo = 0
        tope = TOPE_PANEL if request.user.is_staff else TOPE_SIN_SESION
        if largo > tope:
            return HttpResponse(
                'Lo que intentas enviar pesa demasiado. Si estás subiendo fotos, '
                'súbelas de a menos por vez.',
                status=413, content_type='text/plain; charset=utf-8',
            )
        return self.get_response(request)
