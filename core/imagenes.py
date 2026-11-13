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


def _leer(archivo, lado):
    """Abre la foto subida, la endereza y la deja en RGB. `lado` es el
    tamaño al que se va a terminar achicando: permite abrir un JPEG
    enorme ya reducido."""
    if getattr(archivo, 'size', 0) > PESO_MAXIMO:
        raise FotoInvalida('La foto pesa más de 10 MB. Súbela con menos resolución.')

    imagen = _abrir(archivo)
    try:
        if imagen.format in ('JPEG', 'MPO'):
            # Le pide al decodificador JPEG que abra la foto ya achicada
            # (a la mitad, un cuarto...): una de 48 megapíxeles ocuparía
            # cientos de MB de memoria solo para terminar en 1600 px.
            escala = lado / max(imagen.size)
            if escala < 1:
                imagen.draft('RGB', (math.ceil(imagen.width * escala), math.ceil(imagen.height * escala)))
        imagen = ImageOps.exif_transpose(imagen)
        return _a_rgb(imagen)
    except (OSError, ValueError, SyntaxError):
        raise FotoInvalida('La foto está dañada y no se pudo procesar.')


def _versiones(imagen):
    grande, (ancho, alto) = _webp(imagen, GRANDE)
    miniatura, (mini_ancho, mini_alto) = _webp(imagen, MINIATURA)
    return {
        'grande': grande, 'ancho': ancho, 'alto': alto,
        'miniatura': miniatura, 'mini_ancho': mini_ancho, 'mini_alto': mini_alto,
    }


def procesar_foto(archivo):
    """Recibe el archivo subido y devuelve las dos versiones listas para
    guardar. Lanza FotoInvalida si no sirve."""
    return _versiones(_leer(archivo, GRANDE))


# ---------------------------------------------------------------------
# Foto de portada: se puede recortar, girar y ajustar desde el panel.
#
# Para poder volver a editarla sin perder calidad, de la portada se
# guarda además una versión "original" (enderezada, sin metadatos, hasta
# 2400 px) y los ajustes elegidos. Las versiones que se publican salen
# siempre de aplicar esos ajustes al original.
#
# Los ajustes se aplican en el mismo orden y con las mismas fórmulas que
# los filtros CSS que usa la vista previa del editor
# (core/static/core/js/admin-noticias.js): girar, voltear, recortar, y
# después brillo, contraste y saturación. Así lo que se ve al editar es
# lo que queda publicado.
# ---------------------------------------------------------------------

ORIGINAL = 2400

AJUSTES_POR_DEFECTO = {
    'rotacion': 0, 'voltear': False,
    'x': 0.0, 'y': 0.0, 'ancho': 1.0, 'alto': 1.0,
    'brillo': 1.0, 'contraste': 1.0, 'saturacion': 1.0,
}
RANGOS = {'brillo': (0.5, 1.5), 'contraste': (0.5, 1.5), 'saturacion': (0.0, 2.0)}
RECORTE_MINIMO = 0.05


def procesar_original(archivo):
    """La versión de la portada que se guarda para editarla: WebP de
    alta calidad, hasta 2400 px, sin metadatos."""
    imagen = _leer(archivo, ORIGINAL)
    imagen.thumbnail((ORIGINAL, ORIGINAL), Image.Resampling.LANCZOS)
    salida = io.BytesIO()
    imagen.save(salida, 'WEBP', quality=90, method=4)
    return salida.getvalue()


def _numero(valor, por_defecto, minimo, maximo):
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return por_defecto
    if not math.isfinite(numero):
        return por_defecto
    return min(max(numero, minimo), maximo)


def normalizar_ajustes(datos):
    """Ajustes válidos a partir de lo que mandó el navegador: cualquier
    valor que falte, sobre o esté fuera de rango se corrige acá. Nunca
    falla: en el peor caso devuelve los ajustes por defecto."""
    if not isinstance(datos, dict):
        datos = {}
    ajustes = dict(AJUSTES_POR_DEFECTO)

    try:
        rotacion = int(datos.get('rotacion', 0)) % 360
    except (TypeError, ValueError):
        rotacion = 0
    ajustes['rotacion'] = rotacion if rotacion in (0, 90, 180, 270) else 0
    ajustes['voltear'] = datos.get('voltear') is True

    for clave, (minimo, maximo) in RANGOS.items():
        ajustes[clave] = round(_numero(datos.get(clave), 1.0, minimo, maximo), 3)

    ancho = _numero(datos.get('ancho'), 1.0, RECORTE_MINIMO, 1.0)
    alto = _numero(datos.get('alto'), 1.0, RECORTE_MINIMO, 1.0)
    ajustes['ancho'], ajustes['alto'] = round(ancho, 4), round(alto, 4)
    ajustes['x'] = round(_numero(datos.get('x'), 0.0, 0.0, 1.0 - ancho), 4)
    ajustes['y'] = round(_numero(datos.get('y'), 0.0, 0.0, 1.0 - alto), 4)
    return ajustes


def _lut(funcion):
    return [min(255, max(0, round(funcion(v)))) for v in range(256)] * 3


def aplicar_ajustes(original, ajustes):
    """La imagen editada, a partir del original guardado."""
    ajustes = normalizar_ajustes(ajustes)
    imagen = Image.open(io.BytesIO(bytes(original))).convert('RGB')

    if ajustes['rotacion']:
        # rotate() gira en contra del reloj; la rotación del editor es a
        # favor del reloj, como la de un canvas.
        imagen = imagen.rotate(-ajustes['rotacion'], expand=True)
    if ajustes['voltear']:
        imagen = ImageOps.mirror(imagen)

    ancho, alto = imagen.size
    caja = (
        round(ajustes['x'] * ancho), round(ajustes['y'] * alto),
        round((ajustes['x'] + ajustes['ancho']) * ancho), round((ajustes['y'] + ajustes['alto']) * alto),
    )
    if caja != (0, 0, ancho, alto):
        imagen = imagen.crop(caja)

    # Mismas fórmulas que los filtros CSS brightness(), contrast() y
    # saturate(), en ese orden.
    brillo, contraste, saturacion = ajustes['brillo'], ajustes['contraste'], ajustes['saturacion']
    if brillo != 1:
        imagen = imagen.point(_lut(lambda v: v * brillo))
    if contraste != 1:
        imagen = imagen.point(_lut(lambda v: (v - 127.5) * contraste + 127.5))
    if saturacion != 1:
        s = saturacion
        imagen = imagen.convert('RGB', (
            0.2126 + 0.7874 * s, 0.7152 - 0.7152 * s, 0.0722 - 0.0722 * s, 0,
            0.2126 - 0.2126 * s, 0.7152 + 0.2848 * s, 0.0722 - 0.0722 * s, 0,
            0.2126 - 0.2126 * s, 0.7152 - 0.7152 * s, 0.0722 + 0.9278 * s, 0,
        ))
    return imagen


def derivar(original, ajustes):
    """Las versiones publicables (grande y miniatura) de la portada, con
    los ajustes aplicados."""
    return _versiones(aplicar_ajustes(original, ajustes))


def imagen_social(grande):
    """JPEG de 1200×630 recortado al centro, a partir de la versión
    grande ya procesada. En JPEG y no WebP: WhatsApp y otras redes no
    muestran bien las vistas previas en WebP."""
    imagen = Image.open(io.BytesIO(bytes(grande))).convert('RGB')
    recorte = ImageOps.fit(imagen, SOCIAL, Image.Resampling.LANCZOS)
    salida = io.BytesIO()
    recorte.save(salida, 'JPEG', quality=82, optimize=True)
    return salida.getvalue()
