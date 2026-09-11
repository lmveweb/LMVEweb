import os

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