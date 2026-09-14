from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .seo import PAGINAS


class VistasEstaticas(Sitemap):
    # Dominio y esquema desde SITE_URL, no desde el Host de la petición
    # ni de que el proxy avise que era https: por defecto Django usa
    # request.scheme como protocolo, y detrás de un proxy mal
    # configurado eso da URLs http:// en el sitemap. Son métodos y no
    # atributos de clase para que se lean en cada petición (y para que
    # override_settings funcione en los tests).
    def get_protocol(self, protocol=None):
        return urlsplit(settings.SITE_URL).scheme

    def get_domain(self, site=None):
        return urlsplit(settings.SITE_URL).netloc

    def items(self):
        # Las mismas vistas que tienen metadatos de SEO en core/seo.py:
        # así una página nueva no puede quedar en el sitemap sin title ni
        # description (ni al revés). Nada de /staff/ (redirect) ni del admin.
        return list(PAGINAS)

    def location(self, item):
        return reverse(item)
