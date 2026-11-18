import os

from django.conf import settings
from django.urls import path, include

from core.admin import site as admin_site

# Configurable vía DJANGO_ADMIN_URL para no dejar el panel en la ruta
# adivinable por defecto una vez en producción; sin la variable, sigue
# siendo "admin/" como siempre.
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin/')

urlpatterns = [
    # core.admin.site (no django.contrib.admin.site): exige 2FA además de
    # usuario/clave, ver core/admin.py.
    path(ADMIN_URL, admin_site.urls),
    path('', include('core.urls')),
]

# Páginas de error propias (ver core/errores.py). La del 500 es
# core/templates/500.html, que Django usa sola.
handler404 = 'core.errores.pagina_no_encontrada'
handler403 = 'core.errores.acceso_denegado'

if settings.DEBUG:
    # Solo en local: con DEBUG=True Django muestra su página de
    # depuración en vez de las propias, así que estas direcciones sirven
    # para verlas. En producción no existen.
    from django.core.exceptions import PermissionDenied
    from django.http import Http404
    from django.views.defaults import server_error

    from core.errores import formulario_vencido

    def _vista_previa(request, tipo):
        from core import errores
        if tipo == '404':
            return errores.pagina_no_encontrada(request, Http404())
        if tipo == '403':
            return errores.acceso_denegado(request, PermissionDenied())
        if tipo == 'formulario':
            return formulario_vencido(request)
        return server_error(request)

    urlpatterns.insert(0, path('vista-previa-error/<slug:tipo>/', _vista_previa))
