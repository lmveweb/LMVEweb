"""Procesado de las fotos que se suben desde el admin (Noticias).

Toda foto subida se reescribe antes de guardarse, nunca se guarda el
archivo original:

- Se endereza según su orientación EXIF y después se descartan TODOS
  los metadatos. Las fotos de celular traen la ubicación GPS, y acá son
  fotos de menores de edad.
- Se achica a dos tamaños en WebP: uno para las tarjetas y la página, y
  uno grande para verla ampliada. Una foto de celular de 5 MB queda en
  unos 250 KB entre las dos.

Reescribirla también es lo que la hace segura de servir: lo que sale de
acá son píxeles vueltos a codificar, no los bytes que mandó quien la
subió.
"""

import io
import math

from PIL import Image, ImageOps, UnidentifiedImageError

MINIATURA = 800   # lado mayor, en px: tarjetas y galería
GRANDE = 1600     # lado mayor, en px: foto ampliada
CALIDAD = 80
SOCIAL = (1200, 630)  # vista previa al compartir el link (og:image)

PESO_MAXIMO = 10 * 1024 * 1024
# Tope de píxeles: una imagen comprimida de pocos KB puede declarar un
# tamaño gigantesco y agotar la memoria del servidor al abrirla.
PIXELES_MAXIMOS = 50_000_000
FORMATOS = {'JPEG', 'MPO', 'PNG', 'WEBP'}


class FotoInvalida(ValueError):
    """La foto no se puede usar; el mensaje es para mostrárselo a quien
    la subió."""


def _abrir(archivo):
    archivo.seek(0)
    try:
        imagen = Image.open(archivo)
    except (UnidentifiedImageError, OSError, ValueError):
        raise FotoInvalida('El archivo no es una foto que se pueda leer. Usa JPG, PNG o WebP.')
    if imagen.format not in FORMATOS:
        raise FotoInvalida('Formato de foto no admitido. Usa JPG, PNG o WebP.')
    ancho, alto = imagen.size
    if ancho * alto > PIXELES_MAXIMOS:
        raise FotoInvalida('La foto es demasiado grande. Súbela con menos resolución.')
    return imagen


def _a_rgb(imagen):
    """WebP y JPEG finales van sin transparencia: lo transparente de un
    PNG queda sobre blanco en vez de negro."""
    if imagen.mode in ('RGBA', 'LA') or (imagen.mode == 'P' and 'transparency' in imagen.info):
        imagen = imagen.convert('RGBA')
        fondo = Image.new('RGB', imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.getchannel('A'))
        return fondo
    return imagen.convert('RGB')


def _webp(imagen, lado):
    copia = imagen.copy()
    copia.thumbnail((lado, lado), Image.Resampling.LANCZOS)  # nunca agranda
    salida = io.BytesIO()
    # Sin exif= ni icc_profile=: el archivo sale sin ningún metadato.
    copia.save(salida, 'WEBP', quality=CALIDAD, method=4)
    return salida.getvalue(), copia.size


def procesar_foto(archivo):
    """Recibe el archivo subido y devuelve las dos versiones listas para
    guardar. Lanza FotoInvalida si no sirve."""
    if getattr(archivo, 'size', 0) > PESO_MAXIMO:
        raise FotoInvalida('La foto pesa más de 10 MB. Súbela con menos resolución.')

    imagen = _abrir(archivo)
    try:
        if imagen.format in ('JPEG', 'MPO'):
            # Le pide al decodificador JPEG que abra la foto ya achicada
            # (a la mitad, un cuarto...): una de 48 megapíxeles ocuparía
            # cientos de MB de memoria solo para terminar en 1600 px.
            escala = GRANDE / max(imagen.size)
            if escala < 1:
                imagen.draft('RGB', (math.ceil(imagen.width * escala), math.ceil(imagen.height * escala)))
        imagen = ImageOps.exif_transpose(imagen)
        imagen = _a_rgb(imagen)
    except (OSError, ValueError, SyntaxError):
        raise FotoInvalida('La foto está dañada y no se pudo procesar.')

    grande, (ancho, alto) = _webp(imagen, GRANDE)
    miniatura, (mini_ancho, mini_alto) = _webp(imagen, MINIATURA)
    return {
        'grande': grande, 'ancho': ancho, 'alto': alto,
        'miniatura': miniatura, 'mini_ancho': mini_ancho, 'mini_alto': mini_alto,
    }


def imagen_social(grande):
    """JPEG de 1200×630 recortado al centro, a partir de la versión
    grande ya procesada. En JPEG y no WebP: WhatsApp y otras redes no
    muestran bien las vistas previas en WebP."""
    imagen = Image.open(io.BytesIO(bytes(grande))).convert('RGB')
    recorte = ImageOps.fit(imagen, SOCIAL, Image.Resampling.LANCZOS)
    salida = io.BytesIO()
    recorte.save(salida, 'JPEG', quality=82, optimize=True)
    return salida.getvalue()
