from django.contrib.sitemaps.views import sitemap
from django.urls import path
from django.views.generic import RedirectView, TemplateView

from . import views
from .sitemaps import VistasEstaticas

urlpatterns = [
    path('', views.home, name='home'),
    path('historia/', TemplateView.as_view(template_name='core/proyecto.html'), name='proyecto'),
    path('sobre/', TemplateView.as_view(template_name='core/sobre.html'), name='sobre'),
    path('equipo/', TemplateView.as_view(template_name='core/equipo.html'), name='equipo'),
    path('multimedia/', views.archivo, name='archivo'),
    path('contacto/', views.contacto, name='contacto'),
    path('privacidad/', TemplateView.as_view(template_name='core/privacidad.html'), name='privacidad'),

    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': {'estaticas': VistasEstaticas}},
         name='django.contrib.sitemaps.views.sitemap'),

    # La vista se llamaba "Staff" y vivia en /staff/ hasta el cambio de
    # nombre. El sitio ya esta publicado, asi que cualquier link a la URL
    # vieja que ande dando vueltas seguiria funcionando en vez de tirar
    # 404. El 301 ademas le dice a Google que la direccion buena es la
    # nueva, y que traspase a /equipo/ lo que hubiera indexado de /staff/.
    path('staff/', RedirectView.as_view(pattern_name='equipo', permanent=True)),
]
