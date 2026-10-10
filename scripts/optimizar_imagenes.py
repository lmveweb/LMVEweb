"""Optimiza las imágenes del sitio. Herramienta de desarrollo: se corre en
local y se commitean los archivos que deja; producción no la usa, por eso
Pillow no está en requirements.txt (sí en el venv).

    python scripts/optimizar_imagenes.py

Logos de colegios (core/static/core/img/colegios/): cada PNG/JPG pasa a
WebP de máximo 300×200 px, sin agrandar los más chicos (la placa del
carrusel los muestra a ~122×84, así que alcanza para pantallas de alta
densidad). El original se mueve a originales_imagenes/, que está en el
.gitignore. Después actualiza COLEGIOS en core/contenido.py: la extensión
y las medidas (ancho/alto) que usa el <img> para reservar su espacio.

Para sumar un colegio: deja su logo en la carpeta, agrega su línea en
COLEGIOS con la extensión original y corre este script.

Es idempotente: correrlo de nuevo no reconvierte lo que ya está en WebP.
"""

import re
import shutil
import sys
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parent.parent
ESTATICOS = RAIZ / 'core' / 'static'
COLEGIOS = ESTATICOS / 'core' / 'img' / 'colegios'
ORIGINALES = RAIZ / 'originales_imagenes'
CONTENIDO = RAIZ / 'core' / 'contenido.py'

LOGO_MAXIMO = (300, 200)
CALIDAD_LOGOS = 85  # algo más que en fotos: los bordes y letras se notan
FORMATOS_ORIGINALES = {'.png', '.jpg', '.jpeg'}

# Logos propios del sitio: mantienen nombre y formato PNG (logo-full.png
# lo usan el JSON-LD de core/seo.py y el README). Solo se achican.
LOGOS_DEL_SITIO = {
    'core/img/logo-sobre-oscuro.png': ('alto', 148),  # se muestra a 74 px
    'core/img/logo-full.png': ('ancho', 512),
}


def respaldar(archivo):
    """Mueve el original a originales_imagenes/, con su ruta relativa a
    core/static/ para no pisar archivos con el mismo nombre."""
    destino = ORIGINALES / archivo.relative_to(ESTATICOS)
    destino.parent.mkdir(parents=True, exist_ok=True)
    if destino.exists():
        sys.exit(f'Ya existe {destino}: revisa a mano antes de seguir.')
    shutil.move(archivo, destino)
    return destino


def convertir_logos():
    for original in sorted(COLEGIOS.iterdir()):
        if original.suffix.lower() not in FORMATOS_ORIGINALES:
            continue
        webp = original.with_suffix('.webp')
        with Image.open(original) as im:
            im = im.convert('RGBA' if 'A' in im.getbands() or 'transparency' in im.info else 'RGB')
            im.thumbnail(LOGO_MAXIMO, Image.LANCZOS)
            im.save(webp, 'WEBP', quality=CALIDAD_LOGOS, method=6)
        antes = original.stat().st_size
        respaldar(original)
        print(f'  {original.name}: {antes // 1024} KB -> {webp.name}: {webp.stat().st_size // 1024} KB')


# Una entrada de COLEGIOS por línea, con o sin las medidas ya anotadas.
ENTRADA = re.compile(
    r"\{'src': 'core/img/colegios/(?P<nombre>[^'/]+)\.\w+', "
    r"'alt': (?P<alt>'(?:[^'\\]|\\.)*'|\"[^\"]*\")"
    r"(?:, 'ancho': \d+, 'alto': \d+)?\}"
)


def actualizar_contenido():
    """Apunta cada entrada de COLEGIOS a su WebP y le anota las medidas."""
    texto = CONTENIDO.read_text(encoding='utf-8')
    medidas = {}
    for webp in COLEGIOS.glob('*.webp'):
        with Image.open(webp) as im:
            medidas[webp.stem] = im.size

    usados, sin_archivo = set(), []

    def reemplazar(m):
        nombre = m.group('nombre')
        if nombre not in medidas:
            sin_archivo.append(nombre)
            return m.group(0)
        usados.add(nombre)
        ancho, alto = medidas[nombre]
        return (f"{{'src': 'core/img/colegios/{nombre}.webp', 'alt': {m.group('alt')}, "
                f"'ancho': {ancho}, 'alto': {alto}}}")

    nuevo = ENTRADA.sub(reemplazar, texto)
    if nuevo != texto:
        CONTENIDO.write_text(nuevo, encoding='utf-8')
        print('  core/contenido.py actualizado.')
    for nombre in sin_archivo:
        print(f'  OJO: COLEGIOS menciona "{nombre}" pero no hay logo en la carpeta.')
    for nombre in sorted(set(medidas) - usados):
        print(f'  OJO: {nombre}.webp está en la carpeta pero no en COLEGIOS.')


def achicar_logos_del_sitio():
    for ruta, (lado, medida) in LOGOS_DEL_SITIO.items():
        archivo = ESTATICOS / ruta
        with Image.open(archivo) as im:
            ancho, alto = im.size
            actual = alto if lado == 'alto' else ancho
            if actual <= medida:
                continue
            escala = medida / actual
            chico = im.resize((round(ancho * escala), round(alto * escala)), Image.LANCZOS)
        antes = archivo.stat().st_size
        respaldar(archivo)
        chico.save(archivo, 'PNG', optimize=True)
        print(f'  {ruta}: {ancho}x{alto} ({antes // 1024} KB) -> '
              f'{chico.width}x{chico.height} ({archivo.stat().st_size // 1024} KB)')


if __name__ == '__main__':
    print('Logos de colegios:')
    convertir_logos()
    actualizar_contenido()
    print('Logos del sitio:')
    achicar_logos_del_sitio()
