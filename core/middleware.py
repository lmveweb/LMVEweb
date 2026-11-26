"""Dirección única del sitio y tope de tamaño de lo que se envía.

DominioPropioMiddleware va primero en settings.MIDDLEWARE: manda la
dirección que Render le da al sitio (lmveweb.onrender.com) al dominio
propio, para que haya una sola dirección pública.

TopeDeSubidaMiddleware va después de la autenticación: antes de que
Django lea el cuerpo de un envío (lo hace la protección CSRF, en
cualquier dirección), rechaza los que declaran un tamaño mayor al que el
sitio necesita. Sin esto, cualquiera puede mandar cientos de MB que el
servidor guarda en disco mientras ocupa uno de sus 4 hilos.
"""

from django.conf import settings
from django.http import HttpResponse, HttpResponsePermanentRedirect

MB = 1024 * 1024
# Contacto y el login pesan unos pocos KB.
TOPE_SIN_SESION = 1 * MB
# Una noticia nueva con portada y las 8 fotos de galería, de hasta 10 MB
# cada una (ver core/imagenes.py), más el texto.
TOPE_PANEL = 100 * MB


class DominioPropioMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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
