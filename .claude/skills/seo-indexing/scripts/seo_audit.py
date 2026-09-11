#!/usr/bin/env python3
"""Auditoria de indexacion/SEO tecnico de un sitio, solo con libreria estandar.

Uso:
    python seo_audit.py https://dominio.cl
    python seo_audit.py http://127.0.0.1:8000 --max-pages 20
    python seo_audit.py https://dominio.cl --ua "Mozilla/5.0 ..."

Revisa: variantes http/www y sus redirecciones, robots.txt, sitemap.xml (y
sitemap index), respuesta 404 real, y por cada pagina del sitemap: status,
title, meta description, canonical, meta robots / X-Robots-Tag, lang, H1,
Open Graph, Twitter card, JSON-LD (que parsee y sus @type) e imagenes sin
alt. Al final, titulos/descripciones duplicados y un resumen.

No ejecuta JavaScript: ve exactamente lo que ve un scraper de Open Graph y
la primera pasada de Googlebot. Si algo "falta" aca pero se ve en el
navegador, es que lo esta inyectando JS (ver regla de contenido critico en
el HTML inicial).
"""

import argparse
import ipaddress
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser

UA_POR_DEFECTO = 'Mozilla/5.0 (compatible; seo-audit/1.0)'
NS_SITEMAP = '{http://www.sitemaps.org/schemas/sitemap/0.9}'

OK, AVISO, FALTA = '[OK]   ', '[AVISO]', '[FALTA]'
contadores = {AVISO: 0, FALTA: 0}


def reportar(nivel, texto):
    if nivel in contadores:
        contadores[nivel] += 1
    print(f'  {nivel} {texto}')


@dataclass
class Respuesta:
    url: str
    status: int | None
    headers: dict
    texto: str
    crudo: bytes
    url_final: str
    cadena: list = field(default_factory=list)
    error: str | None = None


class _RegistraRedirecciones(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.cadena = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.cadena.append((code, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def pedir(url, ua, timeout=20):
    registro = _RegistraRedirecciones()
    opener = urllib.request.build_opener(registro)
    req = urllib.request.Request(url, headers={
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    })
    try:
        with opener.open(req, timeout=timeout) as r:
            crudo, status, headers, final = r.read(), r.status, r.headers, r.geturl()
    except urllib.error.HTTPError as e:
        crudo, status, headers, final = e.read(), e.code, e.headers, (e.geturl() or url)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return Respuesta(url, None, {}, '', b'', url, registro.cadena, str(e))
    charset = headers.get_content_charset() or 'utf-8'
    return Respuesta(url, status, dict(headers.items()), crudo.decode(charset, 'replace'),
                     crudo, final, registro.cadena)


class ParserHead(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self.metas, self.links, self.jsonld = [], [], []
        self.lang = None
        self.h1 = 0
        self.imgs = 0
        self.imgs_sin_alt = 0
        self._en_title = False
        self._en_jsonld = False
        self._buf = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or '') for k, v in attrs}
        if tag == 'html':
            self.lang = a.get('lang') or None
        elif tag == 'title' and self.title is None:
            self._en_title, self._buf = True, []
        elif tag == 'meta':
            self.metas.append(a)
        elif tag == 'link':
            self.links.append(a)
        elif tag == 'h1':
            self.h1 += 1
        elif tag == 'img':
            self.imgs += 1
            if 'alt' not in a:
                self.imgs_sin_alt += 1
        elif tag == 'script' and a.get('type', '').strip().lower() == 'application/ld+json':
            self._en_jsonld, self._buf = True, []

    def handle_endtag(self, tag):
        if tag == 'title' and self._en_title:
            self._en_title = False
            self.title = ' '.join(''.join(self._buf).split())
        elif tag == 'script' and self._en_jsonld:
            self._en_jsonld = False
            self.jsonld.append(''.join(self._buf))

    def handle_data(self, data):
        if self._en_title or self._en_jsonld:
            self._buf.append(data)

    def meta(self, clave):
        """Busca por name= o property= (Twitter y OG se mezclan en la practica)."""
        clave = clave.lower()
        for m in self.metas:
            if m.get('name', '').lower() == clave or m.get('property', '').lower() == clave:
                return m.get('content', '')
        return None

    def canonical(self):
        for l in self.links:
            if 'canonical' in l.get('rel', '').lower().split():
                return l.get('href', '')
        return None


def tipos_jsonld(dato):
    tipos = []
    if isinstance(dato, list):
        for d in dato:
            tipos += tipos_jsonld(d)
    elif isinstance(dato, dict):
        if '@graph' in dato:
            tipos += tipos_jsonld(dato['@graph'])
        t = dato.get('@type')
        if t:
            tipos += t if isinstance(t, list) else [t]
    return tipos


def header(resp, nombre):
    for k, v in resp.headers.items():
        if k.lower() == nombre.lower():
            return v
    return None


def es_local(hostname):
    if not hostname or hostname == 'localhost' or hostname.endswith('.localhost'):
        return True
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def seccion(titulo):
    print(f'\n=== {titulo} ===')


def revisar_variantes(base, ua):
    seccion('Version unica del sitio (http/https, www)')
    p = urllib.parse.urlsplit(base)
    host = p.netloc
    canon = f'{p.scheme}://{host}/'
    if es_local(p.hostname):
        reportar(OK, 'host local: se omite la revision de http/www (aplica solo en produccion)')
        return
    alterno = host[4:] if host.startswith('www.') else 'www.' + host
    variantes = [f'http://{host}/', f'https://{alterno}/']
    if p.scheme == 'http':
        variantes = [f'http://{alterno}/']
    for v in variantes:
        r = pedir(v, ua)
        if r.error:
            reportar(AVISO, f'{v} no responde ({r.error}). Si no usas esa variante, esta bien.')
            continue
        codigos = [c for c, _ in r.cadena]
        if r.url_final.rstrip('/') == canon.rstrip('/') and codigos and all(c in (301, 308) for c in codigos):
            reportar(OK, f'{v} -> {r.url_final} ({"/".join(map(str, codigos))})')
        elif r.url_final.rstrip('/') == canon.rstrip('/'):
            reportar(AVISO, f'{v} llega a la canonica pero con redireccion {codigos} (usa 301 permanente)')
        else:
            reportar(FALTA, f'{v} no redirige a {canon} (termina en {r.url_final}, status {r.status}): contenido duplicado')


def revisar_robots(base, ua):
    seccion('robots.txt')
    url = urllib.parse.urljoin(base, '/robots.txt')
    r = pedir(url, ua)
    rp = urllib.robotparser.RobotFileParser()
    if r.status != 200:
        reportar(FALTA, f'{url} responde {r.status or r.error}. Sin robots.txt, los bots asumen "todo permitido", '
                        'pero pierdes la linea Sitemap:')
        rp.parse([])
        return rp, []
    ctype = header(r, 'Content-Type') or ''
    if not ctype.startswith('text/plain'):
        reportar(AVISO, f'Content-Type es "{ctype}", deberia ser text/plain')
    else:
        reportar(OK, '200 text/plain')
    rp.parse(r.texto.splitlines())
    if not rp.can_fetch('Googlebot', base):
        reportar(FALTA, 'robots.txt BLOQUEA a Googlebot en la home (Disallow: / o similar)')
    else:
        reportar(OK, 'Googlebot puede rastrear la home')
    sitemaps = rp.site_maps() or []
    if sitemaps:
        reportar(OK, f'Declara sitemap(s): {", ".join(sitemaps)}')
    else:
        reportar(AVISO, 'No declara ninguna linea "Sitemap: https://.../sitemap.xml"')
    for linea in r.texto.splitlines():
        l = linea.strip().lower()
        if l.startswith('disallow:') and any(s in l for s in ('admin', 'panel', 'staging', 'backup', 'private')):
            reportar(AVISO, f'"{linea.strip()}" publica una ruta sensible: robots.txt es publico, protegela con auth')
    return rp, sitemaps


def urls_de_sitemap(url, ua, profundidad=0):
    r = pedir(url, ua)
    if r.status != 200:
        reportar(FALTA, f'{url} responde {r.status or r.error}')
        return []
    try:
        raiz = ET.fromstring(r.crudo)
    except ET.ParseError as e:
        reportar(FALTA, f'{url} no es XML valido: {e}')
        return []
    tipo = raiz.tag.split('}')[-1]
    locs = [e.text.strip() for e in raiz.iter(NS_SITEMAP + 'loc') if e.text]
    if tipo == 'sitemapindex':
        reportar(OK, f'{url} es un sitemap index con {len(locs)} sitemaps')
        todas = []
        if profundidad < 1:
            for sub in locs:
                todas += urls_de_sitemap(sub, ua, profundidad + 1)
        return todas
    reportar(OK, f'{url}: {len(locs)} URLs')
    return locs


def revisar_404(base, ua):
    seccion('Pagina inexistente')
    url = urllib.parse.urljoin(base, '/esta-ruta-no-existe-seo-audit-7f3a/')
    r = pedir(url, ua)
    if r.status == 404:
        reportar(OK, 'Una ruta inexistente responde 404 real')
    elif r.status == 410:
        reportar(OK, 'Una ruta inexistente responde 410')
    else:
        reportar(FALTA, f'Una ruta inexistente responde {r.status}: soft 404 (tipico de SPA o de un catch-all). '
                        'Google puede indexar paginas vacias')


def revisar_pagina(url, ua, rp, de_sitemap):
    r = pedir(url, ua)
    print(f'\n--- {url}')
    if r.error:
        reportar(FALTA, f'no responde: {r.error}')
        return None
    if r.cadena:
        pasos = ' -> '.join(f'{c} {u}' for c, u in r.cadena)
        nivel = FALTA if de_sitemap else AVISO
        reportar(nivel, f'redirige ({pasos}). En el sitemap solo van URLs finales que responden 200')
    if r.status != 200:
        reportar(FALTA, f'status {r.status}')
        return None
    if not rp.can_fetch('Googlebot', r.url_final):
        reportar(FALTA, 'bloqueada para Googlebot por robots.txt')

    p = ParserHead()
    p.feed(r.texto)

    xrobots = (header(r, 'X-Robots-Tag') or '').lower()
    mrobots = (p.meta('robots') or '').lower()
    if 'noindex' in xrobots or 'noindex' in mrobots:
        reportar(FALTA, f'NOINDEX presente (meta="{mrobots}" header="{xrobots}")')

    if not p.title:
        reportar(FALTA, 'sin <title>')
    elif len(p.title) > 65:
        reportar(AVISO, f'title de {len(p.title)} caracteres, puede truncarse: "{p.title}"')
    elif len(p.title) < 15:
        reportar(AVISO, f'title muy corto: "{p.title}"')
    else:
        reportar(OK, f'title ({len(p.title)}): "{p.title}"')

    desc = p.meta('description')
    if not desc:
        reportar(FALTA, 'sin meta description')
    elif not 50 <= len(desc) <= 170:
        reportar(AVISO, f'description de {len(desc)} caracteres (ideal ~140-160)')
    else:
        reportar(OK, f'description ({len(desc)})')

    canon = p.canonical()
    if not canon:
        reportar(FALTA, 'sin <link rel="canonical">')
    elif not canon.startswith(('http://', 'https://')):
        reportar(FALTA, f'canonical relativa: "{canon}" (debe ser absoluta)')
    elif canon.rstrip('/') != r.url_final.split('?')[0].split('#')[0].rstrip('/'):
        reportar(AVISO, f'canonical apunta a otra URL: {canon} (ok solo si es a proposito)')
    elif urllib.parse.urlsplit(r.url_final).scheme == 'https' and canon.startswith('http://'):
        reportar(FALTA, 'canonical en http:// estando en https (proxy sin configurar?)')
    else:
        reportar(OK, 'canonical absoluta y coherente')

    if not p.lang:
        reportar(AVISO, '<html> sin atributo lang')
    if p.h1 != 1:
        reportar(AVISO, f'{p.h1} etiquetas <h1> (lo normal es exactamente una)')

    faltan_og = [k for k in ('og:title', 'og:description', 'og:image', 'og:url', 'og:type') if not p.meta(k)]
    if faltan_og:
        reportar(AVISO, f'Open Graph incompleto, falta: {", ".join(faltan_og)}')
    else:
        reportar(OK, 'Open Graph completo')
    img = p.meta('og:image')
    if img and not img.startswith(('http://', 'https://')):
        reportar(FALTA, f'og:image relativa ("{img}"): los scrapers la ignoran, debe ser absoluta')
    if not p.meta('twitter:card'):
        reportar(AVISO, 'sin twitter:card (X usa OG como respaldo para lo demas, pero la card la necesita)')

    tipos = []
    for i, bloque in enumerate(p.jsonld, 1):
        try:
            tipos += tipos_jsonld(json.loads(bloque))
        except json.JSONDecodeError as e:
            reportar(FALTA, f'JSON-LD #{i} no parsea: {e}')
    if tipos:
        reportar(OK, f'JSON-LD: {", ".join(tipos)}')
    elif not p.jsonld:
        reportar(AVISO, 'sin datos estructurados JSON-LD')

    if p.imgs_sin_alt:
        reportar(AVISO, f'{p.imgs_sin_alt} de {p.imgs} <img> sin atributo alt (alt="" es valido para decorativas)')

    return {'title': p.title, 'description': desc, 'url': r.url_final}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('base', help='URL base, p. ej. https://dominio.cl')
    ap.add_argument('--max-pages', type=int, default=30, help='maximo de paginas del sitemap a revisar (30)')
    ap.add_argument('--ua', default=UA_POR_DEFECTO, help='User-Agent a usar')
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, ValueError):
        pass

    base = args.base.rstrip('/') + '/'
    print(f'Auditoria SEO de {base}')

    revisar_variantes(base, args.ua)
    rp, declarados = revisar_robots(base, args.ua)

    seccion('sitemap.xml')
    fuentes = declarados or [urllib.parse.urljoin(base, '/sitemap.xml')]
    urls = []
    for s in fuentes:
        urls += urls_de_sitemap(s, args.ua)
    urls = list(dict.fromkeys(urls))
    host_base = urllib.parse.urlsplit(base).netloc
    ajenas = [u for u in urls if urllib.parse.urlsplit(u).netloc != host_base]
    if ajenas:
        reportar(AVISO, f'{len(ajenas)} URLs del sitemap en otro host/esquema, p. ej. {ajenas[0]} '
                        '(normal si auditas local; en produccion deben ser del dominio canonico)')
    if urls and all(u.startswith('http://') for u in urls) and base.startswith('https://'):
        reportar(FALTA, 'el sitemap lista URLs http:// en un sitio https (proxy sin configurar?)')

    revisar_404(base, args.ua)

    seccion('Paginas')
    paginas = [base] + [u for u in urls if u.rstrip('/') != base.rstrip('/')]
    if len(paginas) > args.max_pages:
        print(f'  (revisando {args.max_pages} de {len(paginas)}; usa --max-pages para mas)')
    datos = []
    for u in paginas[:args.max_pages]:
        es_ajena = urllib.parse.urlsplit(u).netloc != host_base
        if es_ajena:
            # Auditando local con un sitemap que apunta a produccion: revisa la ruta en local.
            p = urllib.parse.urlsplit(u)
            u = urllib.parse.urljoin(base, p.path + (f'?{p.query}' if p.query else ''))
        d = revisar_pagina(u, args.ua, rp, de_sitemap=(u != base and not es_ajena))
        if d:
            datos.append(d)

    seccion('Duplicados entre paginas')
    hubo = False
    for campo in ('title', 'description'):
        grupos = defaultdict(list)
        for d in datos:
            if d[campo]:
                grupos[d[campo]].append(d['url'])
        for valor, lista in grupos.items():
            if len(lista) > 1:
                hubo = True
                reportar(AVISO, f'{campo} repetido en {len(lista)} paginas: "{valor[:70]}"')
    if not hubo:
        reportar(OK, 'sin titles ni descriptions repetidos')

    seccion('Resumen')
    print(f'  {contadores[FALTA]} problemas, {contadores[AVISO]} avisos, {len(datos)} paginas revisadas')
    print('  Siguiente paso fuera del codigo: Search Console + sitemap enviado '
          '(ver references/search-console-and-offsite.md)')


if __name__ == '__main__':
    main()
