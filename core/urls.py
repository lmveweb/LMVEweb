from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('historia/', views.proyecto, name='proyecto'),
    path('sobre/', views.sobre, name='sobre'),
    path('multimedia/', views.archivo, name='archivo'),
    path('contacto/', views.contacto, name='contacto'),

    # Material de auspicio. Queda fuera del menú a propósito: sirve para
    # enviarlo por enlace directo a una marca interesada.
    path('impacto/', views.impacto, name='impacto'),
]
