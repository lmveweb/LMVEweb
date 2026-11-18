"""Páginas de error propias, con un mensaje distinto según el caso.

Django las usa en vez de sus pantallas técnicas (en inglés y sin el
diseño del sitio) porque LMVEweb/urls.py las declara como handler404 y
handler403, y settings.CSRF_FAILURE_VIEW apunta a formulario_vencido.
El error 500 es core/templates/500.html, que Django muestra solo.

Dentro del panel, el mensaje sale con el diseño del panel y un enlace de
vuelta a él; en el resto del sitio, con el diseño del sitio. Ninguna se
indexa en Google.

En local (DEBUG=True) Django muestra su página amarilla de depuración en
vez de estas: para verlas, LMVEweb/urls.py monta /vista-previa-error/
solo en ese modo.
"""

from django.shortcuts import render
from django.urls import reverse
from django_ratelimit.exceptions import Ratelimited

from .seo import POR_DEFECTO


def _en_el_panel(request):
    return request.path.startswith(reverse('admin:index'))


def _pagina(request, status, titulo, mensaje, enlaces):
    if _en_el_panel(request):
        from .admin import site
        try:
            contexto = site.each_context(request)
        except Exception:
            contexto = {}
        return render(request, 'core/admin/error.html', {
            **contexto, 'title': titulo, 'mensaje': mensaje,
            'enlaces': [('Volver al inicio del panel', reverse('admin:index'))],
        }, status=status)

    return render(request, 'core/error.html', {
        'codigo': status, 'titulo': titulo, 'mensaje': mensaje, 'enlaces': enlaces,
        # Pisa el SEO del context processor: una página de error no va a
        # Google ni declara una dirección canónica.
        'seo': {**POR_DEFECTO, 'title': f'{titulo} | LMVE', 'indexable': False},
    }, status=status)


def pagina_no_encontrada(request, exception=None):
    if request.path.startswith(reverse('noticias')):
        return _pagina(
            request, 404, 'Noticia no encontrada',
            'Esa noticia no existe o ya no está publicada. Puede que la dirección esté mal '
            'escrita o que la hayan retirado.',
            [('Ver todas las noticias', reverse('noticias')), ('Ir al inicio', reverse('home'))],
        )
    return _pagina(
        request, 404, 'Página no encontrada',
        'No encontramos esta página. Puede que la dirección esté mal escrita o que la '
        'página ya no exista.',
        [('Ir al inicio', reverse('home')), ('Ver las noticias', reverse('noticias')),
         ('Contacto', reverse('contacto'))],
    )


def acceso_denegado(request, exception=None):
    if isinstance(exception, Ratelimited):
        return _pagina(
            request, 403, 'Demasiados intentos',
            'Hubo demasiados intentos seguidos desde tu conexión. Espera un minuto y '
            'vuelve a intentarlo.',
            [('Ir al inicio', reverse('home'))],
        )
    if _en_el_panel(request):
        return _pagina(
            request, 403, 'Sin permiso para esta sección',
            'Tu cuenta no tiene permiso para ver esta sección del panel. Si crees que '
            'deberías poder entrar, pídeselo a quien administra el sitio.',
            [],
        )
    return _pagina(
        request, 403, 'Acceso no permitido',
        'No tienes permiso para ver esta página.',
        [('Ir al inicio', reverse('home'))],
    )


def formulario_vencido(request, reason=''):
    """Falla la protección CSRF: casi siempre, una página que estuvo
    abierta mucho tiempo (la sesión venció o el navegador borró sus
    cookies) y después se envió un formulario."""
    return _pagina(
        request, 403, 'La página estuvo abierta mucho tiempo',
        'Por seguridad, los formularios vencen. Vuelve a la página anterior, recárgala '
        'e inténtalo de nuevo. Si estabas escribiendo un texto largo, cópialo antes de '
        'recargar para no perderlo.',
        [('Ir al inicio', reverse('home'))],
    )
