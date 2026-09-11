import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Mismo escape que usa django.utils.html.json_script: un "</script>" que
# venga dentro de un dato (por ejemplo, en un mensaje de usuario que
# terminara en el JSON-LD) no puede cerrar el bloque antes de tiempo.
_ESCAPES = {ord('<'): '\\u003C', ord('>'): '\\u003E', ord('&'): '\\u0026'}


@register.filter
def jsonld(datos):
    return mark_safe(json.dumps(datos, ensure_ascii=False).translate(_ESCAPES))
