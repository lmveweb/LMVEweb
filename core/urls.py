from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('proyecto/', views.proyecto, name='proyecto'),
    path('impacto/', views.impacto, name='impacto'),
    path('archivo/', views.archivo, name='archivo'),
    path('redes/', views.redes, name='redes'),
    path('contacto/', views.contacto, name='contacto'),
]