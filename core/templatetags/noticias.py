import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

_VINETA = re.compile(r'^\s*[-*•·]\s+(.+)$')
_NUMERO = re.compile(r'^\s*\d{1,3}[.)]\s+(.+)$')
_SUBTITULO = re.compile(r'^\s*#+\s*(.+)$')


@register.filter
def cuerpo_noticia(texto):
    """Convierte el texto plano de una noticia en HTML.

    Quien escribe la noticia no escribe HTML: escribe texto con cuatro
    reglas simples (párrafos separados por una línea en blanco, listas
    con guion, listas numeradas y subtítulos con #). Todo lo que
    escribió se escapa antes de armar las etiquetas, así que por acá no
    puede entrar código al sitio aunque alguien lo pegue en el texto o
    le roben la cuenta a un editor: las únicas etiquetas que salen son
    las que arma esta función.
    """
    bloques = []   # (tipo, [líneas ya escapadas])

    def agregar(tipo, linea):
        if bloques and bloques[-1][0] == tipo and tipo != 'h2':
            bloques[-1][1].append(linea)
        else:
            bloques.append((tipo, [linea]))

    corte = True   # una línea en blanco separa párrafos
    for linea in (texto or '').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if not linea.strip():
            corte = True
            continue
        for tipo, patron in (('h2', _SUBTITULO), ('ul', _VINETA), ('ol', _NUMERO)):
            m = patron.match(linea)
            if m:
                agregar(tipo, escape(m.group(1).strip()))
                break
        else:
            if corte or not bloques or bloques[-1][0] != 'p':
                bloques.append(('p', [escape(linea.strip())]))
            else:
                bloques[-1][1].append(escape(linea.strip()))
        corte = False

    html = []
    for tipo, lineas in bloques:
        if tipo == 'p':
            html.append('<p>' + '<br>'.join(lineas) + '</p>')
        elif tipo == 'h2':
            html.append(f'<h2>{lineas[0]}</h2>')
        else:
            html.append(f'<{tipo}>' + ''.join(f'<li>{li}</li>' for li in lineas) + f'</{tipo}>')
    return mark_safe('\n'.join(html))
