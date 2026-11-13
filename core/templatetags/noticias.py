import re
from urllib.parse import urlsplit

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_VINETA = re.compile(r'^\s*[-*•·]\s+(.+)$')
_NUMERO = re.compile(r'^\s*\d{1,3}[.)]\s+(.+)$')
_SUBTITULO = re.compile(r'^\s*#+\s*(.+)$')

# Un enlace solo en su línea. Solo http(s): nada de "javascript:" ni
# otros esquemas, que es por donde un enlace puede ejecutar código.
_ENLACE_SOLO = re.compile(r'^\s*(https?://\S+)\s*$', re.I)
_ENLACE_EN_TEXTO = re.compile(r'https?://[^\s<]+', re.I)

# El identificador de un video de YouTube son exactamente 11 caracteres
# de este alfabeto. Se valida así de estricto porque termina dentro de
# la dirección de un <iframe>.
_YOUTUBE = re.compile(
    r'^https?://(?:www\.|m\.)?(?:'
    r'youtube\.com/(?:watch\?(?:[^#\s]*&)?v=|(?P<corto>shorts/)|live/|embed/)'
    r'|youtu\.be/)'
    r'(?P<id>[A-Za-z0-9_-]{11})(?:[?&#/].*)?$',
    re.I,
)
_INSTAGRAM = re.compile(
    r'^https?://(?:www\.)?instagram\.com/(?:[A-Za-z0-9_.]+/)?(?P<tipo>p|reel|reels|tv)/(?P<id>[A-Za-z0-9_-]{5,40})(?:[/?#].*)?$',
    re.I,
)

# Redes que no se incrustan (cada una exigiría permitir sus scripts en
# la política de seguridad del sitio): su enlace se muestra como botón.
_NOMBRES = {
    'tiktok.com': 'TikTok', 'facebook.com': 'Facebook', 'fb.watch': 'Facebook',
    'x.com': 'X', 'twitter.com': 'X', 'instagram.com': 'Instagram',
    'youtube.com': 'YouTube', 'youtu.be': 'YouTube', 'vimeo.com': 'Vimeo',
    'drive.google.com': 'Google Drive', 'docs.google.com': 'Google Docs',
}


def _sitio(url):
    host = (urlsplit(url).hostname or '').lower()
    host = host[4:] if host.startswith('www.') else host
    for dominio, nombre in _NOMBRES.items():
        if host == dominio or host.endswith('.' + dominio):
            return nombre
    return host


def _incrustar(url):
    """HTML para un enlace que venía solo en su línea: el video o la
    publicación incrustada si es de YouTube o Instagram, y un botón que
    abre el enlace en cualquier otro caso."""
    m = _YOUTUBE.match(url)
    if m:
        clase = 'noticia-video noticia-video--vertical' if m.group('corto') else 'noticia-video'
        # youtube-nocookie: el modo de YouTube que no deja cookies de
        # seguimiento hasta que la persona le da a reproducir.
        # referrerpolicy: el sitio no envía "de dónde vienes" a terceros
        # (Referrer-Policy: same-origin) y YouTube se niega a reproducir
        # sin ese dato; acá se le manda solo el dominio, no la página.
        return (
            f'<div class="{clase}"><iframe src="https://www.youtube-nocookie.com/embed/{m.group("id")}" '
            'title="Video de YouTube" loading="lazy" allowfullscreen '
            'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe></div>'
        )

    m = _INSTAGRAM.match(url)
    if m:
        tipo = 'reel' if m.group('tipo').lower().startswith('reel') else m.group('tipo').lower()
        permalink = f'https://www.instagram.com/{tipo}/{m.group("id")}/'
        # Mismo marcado que los posts de la portada: lo completa el
        # embed.js de Instagram. Sin JavaScript queda el enlace.
        return (
            f'<div class="noticia-instagram"><blockquote class="instagram-media" '
            f'data-instgrm-permalink="{permalink}" data-instgrm-version="14">'
            f'<a href="{permalink}" target="_blank" rel="noopener noreferrer">Ver esta publicación en Instagram</a>'
            '</blockquote></div>'
        )

    return (
        f'<p><a class="noticia-enlace" href="{escape(url)}" target="_blank" rel="noopener noreferrer">'
        f'Ver en {escape(_sitio(url))}</a></p>'
    )


def _con_enlaces(texto_escapado):
    """Convierte en enlaces las direcciones escritas dentro de un texto
    ya escapado. La puntuación pegada al final (el punto de la frase)
    queda fuera del enlace."""
    def reemplazo(m):
        url = m.group(0)
        cola = ''
        while url and url[-1] in '.,;:!?)':
            url, cola = url[:-1], url[-1] + cola
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>{cola}'
    return _ENLACE_EN_TEXTO.sub(reemplazo, texto_escapado)


@register.filter
def cuerpo_noticia(texto):
    """Convierte el texto plano de una noticia en HTML.

    Quien escribe la noticia no escribe HTML: escribe texto con unas
    pocas reglas (párrafos separados por una línea en blanco, listas con
    guion, listas numeradas, subtítulos con # y un enlace solo en una
    línea para incrustar un video o una publicación). Todo lo que
    escribió se escapa antes de armar las etiquetas, así que por acá no
    puede entrar código al sitio aunque alguien lo pegue en el texto o
    le roben la cuenta a un editor: las únicas etiquetas que salen son
    las que arma este archivo.
    """
    bloques = []   # (tipo, [fragmentos de HTML ya seguros])

    def agregar(tipo, fragmento):
        if bloques and bloques[-1][0] == tipo and tipo in ('ul', 'ol'):
            bloques[-1][1].append(fragmento)
        else:
            bloques.append((tipo, [fragmento]))

    corte = True   # una línea en blanco separa párrafos
    for linea in (texto or '').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if not linea.strip():
            corte = True
            continue

        enlace = _ENLACE_SOLO.match(linea)
        if enlace:
            agregar('html', _incrustar(enlace.group(1)))
            corte = True
            continue

        for tipo, patron in (('h2', _SUBTITULO), ('ul', _VINETA), ('ol', _NUMERO)):
            m = patron.match(linea)
            if m:
                contenido = escape(m.group(1).strip())
                agregar(tipo, contenido if tipo == 'h2' else _con_enlaces(contenido))
                break
        else:
            contenido = _con_enlaces(escape(linea.strip()))
            if corte or not bloques or bloques[-1][0] != 'p':
                bloques.append(('p', [contenido]))
            else:
                bloques[-1][1].append(contenido)
        corte = False

    html = []
    for tipo, partes in bloques:
        if tipo == 'html':
            html.append(partes[0])
        elif tipo == 'p':
            html.append('<p>' + '<br>'.join(partes) + '</p>')
        elif tipo == 'h2':
            html.append(f'<h2>{partes[0]}</h2>')
        else:
            html.append(f'<{tipo}>' + ''.join(f'<li>{li}</li>' for li in partes) + f'</{tipo}>')
    return mark_safe('\n'.join(html))
