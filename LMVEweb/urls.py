import os

from django.contrib import admin
from django.urls import path, include

# Configurable vía DJANGO_ADMIN_URL para no dejar el panel en la ruta
# adivinable por defecto una vez en producción; sin la variable, sigue
# siendo "admin/" como siempre.
ADMIN_URL = os.environ.get('DJANGO_ADMIN_URL', 'admin/')

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('', include('core.urls')),
]