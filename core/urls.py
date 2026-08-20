from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('historia/', views.proyecto, name='proyecto'),
    path('sobre/', views.sobre, name='sobre'),
    path('staff/', views.staff, name='staff'),
    path('multimedia/', views.archivo, name='archivo'),
    path('contacto/', views.contacto, name='contacto'),
    path('privacidad/', views.privacidad, name='privacidad'),
]
