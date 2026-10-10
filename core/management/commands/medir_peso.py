import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client
from django.test.utils import override_settings
from django.urls import reverse

from core.seo import PAGINAS

# Lo que el navegador nunca descarga aunque esté en el HTML: la og:image
# va en un <meta> para las redes, y el logo del JSON-LD es para Google.
# Si se contaran, la portada pesaría 1,3 MB más de lo que pesa de verdad.
# También los <source media="..."> de un <picture>: son la alternativa
# para pantallas grandes, así que la medición es la de un celular (igual
# que con el video del hero, que solo carga en escritorio).
SIN_DESCARGA = re.compile(
    r'<script[^>]*type="application/ld\+json"[^>]*>.*?</script>'
    r'|<meta\b[^>]*>'
    r'|<source\b[^>]*\bmedia=[^>]*>',
    re.S | re.I,
)
BLOQUE_SCRIPT = re.compile(r'<script\b[^>]*>(.*?)</script>', re.S | re.I)
# data-src, data-src-completo, data-poster, etc.: el navegador no descarga
# nada de un atributo data-*; si la ruta se usa, la asigna el JavaScript.
ATRIBUTO_DIFERIDO = re.compile(r'\bdata-[\w-]+\s*=\s*"([^"]*)"', re.I)


def clasificar_estaticos(html, prefijo='/static/'):
    """Separa los estáticos que referencia una página en dos conjuntos de
    rutas relativas a STATIC_ROOT: los de la carga inicial y los que trae
    el JavaScript después (dentro de un <script> o en un data-*). Si un
    archivo aparece en los dos lados, cuenta como carga inicial."""
    ruta = re.compile(re.escape(prefijo) + r'''([^"'\s)?#]+)''')
    html = SIN_DESCARGA.sub('', html)

    diferidos = set()
    for bloque in BLOQUE_SCRIPT.findall(html):
        diferidos.update(ruta.findall(bloque))
    html = BLOQUE_SCRIPT.sub(lambda m: m.group(0).split('>', 1)[0] + '>', html)

    for valor in ATRIBUTO_DIFERIDO.findall(html):
        diferidos.update(ruta.findall(valor))
    html = ATRIBUTO_DIFERIDO.sub('', html)

    iniciales = set(ruta.findall(html))
    return iniciales, diferidos - iniciales


def kb(bytes_):
    return f'{bytes_ / 1024:,.0f} KB'.replace(',', '.')


class Command(BaseCommand):
    help = (
        'Mide cuánto descarga cada vista pública: renderiza las páginas de '
        'core.seo.PAGINAS, busca los /static/ que referencian y suma su peso '
        'en STATIC_ROOT (cada archivo una vez por página). Separa la carga '
        'inicial de lo que trae el JavaScript después. Requiere haber '
        'corrido collectstatic antes. Las fuentes del CSS se cuentan todas, '
        'aunque el navegador solo baja las que usa: es un tope, no un piso.'
    )

    def handle(self, **options):
        raiz = Path(settings.STATIC_ROOT)
        if not raiz.is_dir():
            raise CommandError(f'No existe {raiz}. Corre "python manage.py collectstatic" primero.')

        prefijo = '/' + settings.STATIC_URL.strip('/') + '/'
        # Fuera de "manage.py test" el host de Client() no está permitido
        # y Django responde 400; acá da lo mismo el host, solo se mide.
        with override_settings(ALLOWED_HOSTS=['testserver']):
            cliente = Client()
            for nombre in PAGINAS:
                self._medir(cliente, nombre, raiz, prefijo)

    def _medir(self, cliente, nombre, raiz, prefijo):
        url = reverse(nombre)
        respuesta = cliente.get(url)
        if respuesta.status_code != 200:
            self.stderr.write(f'{url}: respondió {respuesta.status_code}, se omite.')
            return

        iniciales, diferidos = clasificar_estaticos(respuesta.content.decode(), prefijo)
        pesos, faltantes = {}, []
        for archivo in iniciales | diferidos:
            ruta = raiz / archivo
            if ruta.is_file():
                pesos[archivo] = ruta.stat().st_size
            else:
                faltantes.append(archivo)

        inicial = sum(pesos.get(a, 0) for a in iniciales)
        diferido = sum(pesos.get(a, 0) for a in diferidos)
        self.stdout.write(self.style.MIGRATE_HEADING(f'{url}  ({nombre})'))
        self.stdout.write(
            f'  Carga inicial: {kb(inicial)} | Por JS: {kb(diferido)} | '
            f'Archivos: {len(pesos)}'
        )
        for archivo, peso in sorted(pesos.items(), key=lambda p: -p[1])[:5]:
            marca = ' (JS)' if archivo in diferidos else ''
            self.stdout.write(f'    {kb(peso):>9}  {archivo}{marca}')
        for archivo in sorted(faltantes):
            self.stderr.write(f'  No está en {raiz.name}/: {archivo}')
