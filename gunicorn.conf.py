"""Configuración de Gunicorn. Se carga sola: Gunicorn busca este archivo
en la carpeta desde la que arranca, sin tener que nombrarlo en el
comando de inicio del hosting.

Hilos en vez de un proceso que atiende de a una petición: con un solo
worker sincrónico, mientras alguien sube las fotos de una noticia desde
el admin (o mientras el sitio espera a Gmail o a Turnstile en el
formulario de Contacto) el sitio entero queda sin responderle a nadie
más. Con hilos, esas esperas no bloquean al resto.

La cantidad de procesos sigue saliendo de WEB_CONCURRENCY, como antes.
"""

threads = 4

# Subir varias fotos de celular desde una red lenta puede tardar más que
# los 30 segundos por defecto.
timeout = 120
