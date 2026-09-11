# Python: Django, Flask, FastAPI

Todos renderizan en el servidor, así que el HTML inicial ya trae las meta: el trabajo es producirlas bien y servir `robots.txt` y `sitemap.xml`.

---

## Django

### 1. Configuración

```python
# settings.py
INSTALLED_APPS += ['django.contrib.sitemaps']   # trae el template sitemap.xml

# Origen canónico del sitio, sin barra final. Todas las URLs absolutas
# (canonical, og:url, og:image, sitemap, robots) salen de acá y no del
# header Host de la petición.
SITE_URL = os.environ.get('SITE_URL', 'http://127.0.0.1:8000').rstrip('/')

TEMPLATES[0]['OPTIONS']['context_processors'] += ['core.seo.contexto_seo']
```

**Detrás de un proxy que termina el TLS** (Render, Heroku, Railway, Nginx), `request.scheme` puede ser `http` aunque el visitante entró por https. Si algo del proyecto usa `request.build_absolute_uri()`, configura:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

**Solo** si el proxy siempre fija o limpia ese header (Render y Heroku lo hacen). Si no, cualquiera podría mandarlo falsificado. Antes de agregarlo, revisa que el sitio no dependa ya de Gunicorn con `forwarded_allow_ips` (en ese caso el esquema ya llega bien). Construir desde `SITE_URL` evita el problema en ambos casos.

No hace falta `django.contrib.sites`: sin esa app, el sitemap usa el host de la petición. La clase de abajo igual fija dominio y esquema desde `SITE_URL`.

### 2. Metadatos por página, en un solo lugar

En Django un `{% block %}` no se puede imprimir dos veces, así que `{% block title %}` no sirve también para `og:title`. El patrón limpio: un diccionario por nombre de URL y un context processor.

```python
# core/seo.py
from django.conf import settings

POR_DEFECTO = {
    'title': 'Marca | Propuesta corta',
    'description': 'Descripción general del sitio, ~150 caracteres, escrita para humanos.',
    'og_image': 'core/img/og-default.jpg',   # ruta de static, 1200x630
    'indexable': True,
}

PAGINAS = {
    'home': {
        'title': 'Nombre completo (SIGLA) | Propuesta corta',
        'description': '…',
    },
    'historia': {'title': 'Historia | SIGLA', 'description': '…'},
    'gracias': {'title': 'Gracias | SIGLA', 'indexable': False},
}


def contexto_seo(request):
    match = getattr(request, 'resolver_match', None)
    nombre = match.url_name if match else None
    return {
        'SITE_URL': settings.SITE_URL,
        'seo': {**POR_DEFECTO, **PAGINAS.get(nombre, {})},
        'canonical_url': settings.SITE_URL + request.path,
    }
```

Si la vista muestra un objeto (noticia, producto), la vista pasa su propio `seo` en el contexto y pisa al del context processor (el contexto de la vista gana).

```django
{# base.html, dentro de <head> #}
{% load static seo %}
<title>{% block title %}{{ seo.title }}{% endblock %}</title>
<meta name="description" content="{{ seo.description }}">
{% if seo.indexable %}
<link rel="canonical" href="{{ canonical_url }}">
{% else %}
<meta name="robots" content="noindex, follow">
{% endif %}

<meta property="og:type" content="website">
<meta property="og:site_name" content="SIGLA">
<meta property="og:locale" content="es_CL">
<meta property="og:title" content="{{ seo.og_title|default:seo.title }}">
<meta property="og:description" content="{{ seo.description }}">
<meta property="og:url" content="{{ canonical_url }}">
<meta property="og:image" content="{{ SITE_URL }}{% static seo.og_image %}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">

{% if jsonld %}
<script type="application/ld+json" nonce="{{ request.csp_nonce }}">{{ jsonld|jsonld }}</script>
{% endif %}
```

- `{% static %}` devuelve una ruta relativa (con hash si usas `ManifestStaticFilesStorage`/WhiteNoise); anteponerle `SITE_URL` la deja absoluta, que es lo que exigen los scrapers.
- El `nonce` solo si el proyecto usa django-csp; si no, sácalo.
- Django autoescapa `{{ seo.description }}` dentro del atributo: comillas y `<` quedan seguros.

### 3. Helper de JSON-LD con escape

```python
# core/templatetags/seo.py
import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# Mismo escape que usa django.utils.html.json_script: un "</script>" dentro
# de un dato no puede cerrar el bloque.
_ESCAPES = {ord('<'): '\\u003C', ord('>'): '\\u003E', ord('&'): '\\u0026'}


@register.filter
def jsonld(datos):
    return mark_safe(json.dumps(datos, ensure_ascii=False).translate(_ESCAPES))
```

Los datos se arman en Python (no a mano en el template) y la vista de la home los pasa:

```python
# core/seo.py
def jsonld_home():
    url = settings.SITE_URL + '/'
    org_id = url + '#organizacion'
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'WebSite', '@id': url + '#sitio', 'url': url,
             'name': 'Nombre completo', 'alternateName': ['SIGLA'],
             'inLanguage': 'es-CL', 'publisher': {'@id': org_id}},
            {'@type': 'SportsOrganization', '@id': org_id, 'url': url,
             'name': 'Nombre completo', 'alternateName': 'SIGLA',
             'logo': settings.SITE_URL + static('core/img/logo-512.png'),
             'sameAs': ['https://www.instagram.com/cuenta_oficial/']},
        ],
    }

# core/views.py
def home(request):
    return render(request, 'core/home.html', {'jsonld': jsonld_home()})
```

(`static` es `django.templatetags.static.static`.) Ver qué propiedades poner según el tipo de entidad en `metadata-and-structured-data.md`.

### 4. sitemap.xml

```python
# core/sitemaps.py
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class VistasEstaticas(Sitemap):
    # Esquema y dominio desde SITE_URL: no dependen del Host de la
    # petición ni de que el proxy avise que era https. Por defecto Django
    # usa request.scheme como protocolo, y detrás de un proxy mal
    # configurado eso da URLs http://. Métodos y no atributos de clase:
    # así se leen en cada petición y override_settings funciona en tests.
    def get_protocol(self, protocol=None):
        return urlsplit(settings.SITE_URL).scheme

    def get_domain(self, site=None):
        return urlsplit(settings.SITE_URL).netloc

    def items(self):
        # Solo vistas públicas e indexables. Nada de admin, gracias, etc.
        return ['home', 'historia', 'sobre', 'contacto']

    def location(self, item):
        return reverse(item)
```

`get_domain()` y `get_protocol()` existen en las versiones modernas de Django; si trabajas con una antigua, confírmalo con `grep -n "def get_domain" <venv>/…/django/contrib/sitemaps/__init__.py`.

Para modelos (noticias, productos): otra clase con `items()` devolviendo el queryset publicado y `lastmod()` devolviendo el campo de fecha de modificación **real**. Se agregan las dos al diccionario `sitemaps`.

```python
# urls.py (el del proyecto)
from django.contrib.sitemaps.views import sitemap
from core.sitemaps import VistasEstaticas
from core import views

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': {'estaticas': VistasEstaticas}},
         name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.robots_txt),
    # ...
]
```

### 5. robots.txt

```python
# core/views.py
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


@require_GET
@cache_control(max_age=60 * 60 * 24, public=True)
def robots_txt(request):
    lineas = [
        'User-agent: *',
        'Allow: /',
        '',
        f'Sitemap: {settings.SITE_URL}/sitemap.xml',
    ]
    return HttpResponse('\n'.join(lineas) + '\n', content_type='text/plain; charset=utf-8')
```

No agregues `Disallow:` para el admin, sobre todo si su URL es configurable (`DJANGO_ADMIN_URL`): el admin ya pide login, y listarlo lo delataría.

### 6. Tests

```python
import json
import re

from django.test import TestCase, override_settings
from django.urls import reverse

PUBLICAS = ['home', 'historia', 'sobre', 'contacto']


@override_settings(SITE_URL='https://dominio.cl')
class SeoTests(TestCase):
    def test_robots(self):
        r = self.client.get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/plain'))
        self.assertContains(r, 'Sitemap: https://dominio.cl/sitemap.xml')

    def test_sitemap_lista_las_publicas_con_dominio_canonico(self):
        r = self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        for nombre in PUBLICAS:
            self.assertContains(r, f'<loc>https://dominio.cl{reverse(nombre)}</loc>')

    def test_cada_publica_tiene_meta(self):
        for nombre in PUBLICAS:
            r = self.client.get(reverse(nombre))
            self.assertContains(r, '<meta name="description"')
            self.assertContains(r, f'<link rel="canonical" href="https://dominio.cl{reverse(nombre)}">')
            self.assertContains(r, 'property="og:image" content="https://dominio.cl/')

    def test_jsonld_de_la_home_parsea(self):
        r = self.client.get(reverse('home'))
        bloque = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', r.content.decode(), re.S)
        self.assertIsNotNone(bloque)
        datos = json.loads(bloque.group(1))
        tipos = [n['@type'] for n in datos['@graph']]
        self.assertIn('WebSite', tipos)
```

### 7. Verificar

```bash
python manage.py test
python manage.py runserver
python .claude/skills/seo-indexing/scripts/seo_audit.py http://127.0.0.1:8000
```

En local el sitemap va a listar `SITE_URL` (producción, si está en el `.env`) y la auditoría te avisará que son de otro host: es esperable; revisa las rutas localmente igual. Después del deploy, corre la auditoría contra el dominio real.

---

## Flask

```python
from flask import Flask, Response, render_template, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['PREFERRED_URL_SCHEME'] = 'https'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)   # solo detrás de UN proxy de confianza

PUBLICAS = ['index', 'historia', 'contacto']


@app.get('/robots.txt')
def robots():
    cuerpo = f"User-agent: *\nAllow: /\n\nSitemap: {url_for('sitemap', _external=True)}\n"
    return Response(cuerpo, mimetype='text/plain')


@app.get('/sitemap.xml')
def sitemap():
    urls = [url_for(e, _external=True) for e in PUBLICAS]
    return Response(render_template('sitemap.xml', urls=urls), mimetype='application/xml')
```

```jinja
{# templates/sitemap.xml #}
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{% for u in urls %}  <url><loc>{{ u }}</loc></url>
{% endfor %}</urlset>
```

Meta: bloques Jinja en `base.html` (`{% block description %}`); a diferencia de Django, en Jinja puedes reutilizar un bloque con `{{ self.title() }}`, lo que sirve para `og:title`. JSON-LD: `{{ datos|tojson }}` de Jinja ya escapa `<`, `>`, `&` y `'`.

## FastAPI

```python
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, Response
from fastapi.templating import Jinja2Templates

SITE_URL = 'https://dominio.cl'
app = FastAPI()
templates = Jinja2Templates(directory='templates')


@app.get('/robots.txt', response_class=PlainTextResponse)
def robots():
    return f'User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n'


@app.get('/sitemap.xml')
def sitemap():
    rutas = ['/', '/historia', '/contacto']
    locs = ''.join(f'<url><loc>{SITE_URL}{r}</loc></url>' for r in rutas)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>'
           f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{locs}</urlset>')
    return Response(content=xml, media_type='application/xml')
```

Si FastAPI solo es una API detrás de un frontend JS, el SEO se resuelve en el frontend (ver `javascript.md`), no acá. Detrás de un proxy, arranca uvicorn con `--proxy-headers --forwarded-allow-ips=<ip del proxy>` para que `request.url` sea https.
