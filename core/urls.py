from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('historia/', views.proyecto, name='proyecto'),
    path('sobre/', views.sobre, name='sobre'),
    path('equipo/', views.equipo, name='equipo'),
    path('multimedia/', views.archivo, name='archivo'),
    path('contacto/', views.contacto, name='contacto'),
    path('privacidad/', views.privacidad, name='privacidad'),

    # La vista se llamaba "Staff" y vivia en /staff/ hasta el cambio de
    # nombre. El sitio ya esta publicado, asi que cualquier link a la URL
    # vieja que ande dando vueltas seguiria funcionando en vez de tirar
    # 404. El 301 ademas le dice a Google que la direccion buena es la
    # nueva, y que traspase a /equipo/ lo que hubiera indexado de /staff/.
    path('staff/', RedirectView.as_view(pattern_name='equipo', permanent=True)),
]
