"""IP del visitante, para el límite de intentos y los registros.

Detrás del proxy del hosting, REMOTE_ADDR es la dirección del proxy: la
misma para todos los visitantes. Un límite "por IP" calculado con ese
valor es un solo cupo compartido, y a cualquiera le alcanza con gastarlo
para dejar el formulario de Contacto (o el login del admin) sin
funcionar para los demás.

La IP real la entrega el proxy en un encabezado, y cuál es depende del
hosting: por eso es configurable (settings.IP_CLIENTE_ENCABEZADO, desde
la variable de entorno DJANGO_CLIENT_IP_HEADER) y viene apagado por
defecto. Un encabezado lo puede escribir cualquiera; solo es confiable
si el proxy lo pisa siempre con el valor verdadero, así que confiar en
uno sin saber que el hosting lo pone regalaría una forma de saltarse el
límite cambiándolo en cada intento.

Cloudflare lo pisa siempre, pero a Render también se puede llegar
directo, sin pasar por Cloudflare. Por eso, si hay una clave configurada
(settings.PROXY_CLAVE, desde DJANGO_PROXY_SECRET), el encabezado solo se
usa cuando la visita trae esa clave, que agrega Cloudflare (lo revisa
core/middleware.py).
"""

import ipaddress

from django.conf import settings


def ip_cliente(request):
    """La IP del visitante: la del encabezado configurado si trae una
    IP válida, y si no la de la conexión (REMOTE_ADDR)."""
    conexion = request.META.get('REMOTE_ADDR', '')
    encabezado = settings.IP_CLIENTE_ENCABEZADO
    if not encabezado:
        return conexion
    if settings.PROXY_CLAVE and not getattr(request, 'origen_verificado', False):
        return conexion

    valor = request.META.get('HTTP_' + encabezado.upper().replace('-', '_'), '').strip()
    try:
        # Tiene que ser exactamente una IP. Una lista separada por comas
        # (como la de X-Forwarded-For) no sirve: sus primeros valores
        # son los que puede inventar el visitante.
        return str(ipaddress.ip_address(valor))
    except ValueError:
        return conexion


def clave_ratelimit(group, request):
    """Clave para django-ratelimit (key=clave_ratelimit).

    En IPv6 se agrupa por bloque /64, que es lo que se le asigna a una
    casa u oficina: contando por dirección exacta, bastaría con cambiar
    los últimos dígitos en cada intento para no toparse con el límite.
    """
    ip = ip_cliente(request)
    try:
        direccion = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if direccion.version == 6:
        return str(ipaddress.ip_network(f'{direccion}/64', strict=False).network_address)
    return ip
