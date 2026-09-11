"""Metadatos de SEO (title, description, canonical, Open Graph) por vista.

En Python, no en las plantillas, por la misma razón que COLEGIOS y
FOTOS_MULTIMEDIA en views.py: ajustar el texto de una vista es editar
una línea acá, sin tocar HTML. El diccionario se indexa por el nombre
de URL (`request.resolver_match.url_name`), y contexto_seo() lo entrega
a cada plantilla vía context processor, así que ninguna vista necesita
pasarlo a mano.
"""

from django.conf import settings
from django.templatetags.static import static

POR_DEFECTO = {
    'title': 'LMVE | Liga Metropolitana de Voleibol Escolar',
    'description': (
        'Liga Metropolitana de Voleibol Escolar (LMVE), fundada en 1987: historia, colegios '
        'participantes y multimedia de la competencia escolar de voleibol en Santiago.'
    ),
    'og_image': 'core/img/fotos/impacto-banner-sponsor.jpg',
    'indexable': True,
}

PAGINAS = {
    'home': {
        'title': 'LMVE | Liga Metropolitana de Voleibol Escolar',
        'description': POR_DEFECTO['description'],
    },
    'proyecto': {
        'title': 'Historia | LMVE',
        'description': (
            'La historia de la Liga Metropolitana de Voleibol Escolar desde su fundación '
            'en 1987: épocas, hitos y protagonistas del voleibol escolar en Santiago.'
        ),
    },
    'sobre': {
        'title': 'Sobre la LMVE | LMVE',
        'description': (
            'Visión y misión de la Liga Metropolitana de Voleibol Escolar, la organización '
            'que reúne a colegios de la Región Metropolitana en torno al voleibol escolar.'
        ),
    },
    'equipo': {
        'title': 'Equipo y Directiva | LMVE',
        'description': (
            'Directiva, coordinadores y equipo detrás de la Liga Metropolitana de '
            'Voleibol Escolar.'
        ),
    },
    'archivo': {
        'title': 'Multimedia | LMVE',
        'description': (
            'Galería de fotos de la Liga Metropolitana de Voleibol Escolar: partidos, '
            'jornadas y momentos de la competencia escolar de voleibol.'
        ),
        'og_image': 'core/img/fotos/galeria-4.jpg',
    },
    'contacto': {
        'title': 'Contacto | LMVE',
        'description': (
            'Contáctate con la Liga Metropolitana de Voleibol Escolar para propuestas '
            'de auspicio y patrocinio.'
        ),
    },
    'privacidad': {
        'title': 'Política de Privacidad | LMVE',
        'description': (
            'Política de privacidad y uso de datos de la Liga Metropolitana de '
            'Voleibol Escolar.'
        ),
    },
}


def contexto_seo(request):
    """Context processor: agrega `seo`, `canonical_url` y `SITE_URL` a
    cada plantilla renderizada con RequestContext (o sea, cualquier
    render() normal), sin que cada vista tenga que pasarlos a mano."""
    match = getattr(request, 'resolver_match', None)
    nombre = match.url_name if match else None
    seo = {**POR_DEFECTO, **PAGINAS.get(nombre, {})}
    return {
        'SITE_URL': settings.SITE_URL,
        'seo': seo,
        'canonical_url': settings.SITE_URL + request.path,
        'og_image_url': settings.SITE_URL + static(seo['og_image']),
    }


def jsonld_home():
    """WebSite + SportsOrganization de la home, con alternateName: es lo
    que Google usa para el nombre del sitio en los resultados, y ataca
    directo el problema de que "LMVE" compita con la liga de béisbol
    mexicana (LMBE) en la búsqueda."""
    url = settings.SITE_URL + '/'
    org_id = url + '#organizacion'
    return {
        '@context': 'https://schema.org',
        '@graph': [
            {
                '@type': 'WebSite',
                '@id': url + '#sitio',
                'url': url,
                'name': 'Liga Metropolitana de Voleibol Escolar',
                'alternateName': ['LMVE', 'Liga Metropolitana de Vóleibol Escolar'],
                'inLanguage': 'es-CL',
                'publisher': {'@id': org_id},
            },
            {
                '@type': 'SportsOrganization',
                '@id': org_id,
                'name': 'Liga Metropolitana de Voleibol Escolar',
                'alternateName': 'LMVE',
                'url': url,
                'logo': settings.SITE_URL + static('core/img/logo-full.png'),
                'description': POR_DEFECTO['description'],
                'foundingDate': '1987',
                'sport': 'Voleibol',
                'slogan': 'Educar a Través del Deporte',
                'areaServed': {
                    '@type': 'AdministrativeArea',
                    'name': 'Región Metropolitana de Santiago',
                },
                'address': {
                    '@type': 'PostalAddress',
                    'addressLocality': 'Santiago',
                    'addressRegion': 'Región Metropolitana',
                    'addressCountry': 'CL',
                },
                'email': 'ligametropolitanave@gmail.com',
                'sameAs': [
                    'https://www.instagram.com/ligametropolitanavoley/',
                ],
            },
        ],
    }
