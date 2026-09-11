---
name: seo-indexing
description: Implementa y audita la indexación y el SEO técnico de sitios web — robots.txt, sitemap.xml, title/meta description, canonical, Open Graph y Twitter cards, datos estructurados JSON-LD (schema.org), redirecciones http/www, soft 404 y alta en Google Search Console y Bing — en Django, Flask, FastAPI, Next.js, React (Vite/SPA), Nuxt/Vue, Astro, SvelteKit, Express, HTML estático, Laravel, WordPress, Spring Boot, Rails y ASP.NET Core. Úsala SIEMPRE que el usuario mencione SEO, indexar o indexación, posicionamiento, "que mi página aparezca en Google", Search Console, sitemap, robots.txt, meta tags, Open Graph, la vista previa de un link en WhatsApp o redes, datos estructurados, schema.org, rich results, canonical, o que el buscador confunde su sitio o su sigla con otro.
---

# Indexación y SEO técnico

Casi todo "no aparezco en Google" es un problema de que el buscador **no puede llegar** o **no sabe qué indexar**, no de palabras clave. Esta skill ataca el problema en capas, de abajo hacia arriba, y verifica cada una con HTTP (sin navegador).

## Las cinco capas, en orden de dependencia

| # | Capa | La pregunta | Piezas |
|---|---|---|---|
| 1 | **Rastreable** | ¿Puede el bot llegar y leer el HTML? | `robots.txt`, `sitemap.xml`, códigos HTTP reales (200/301/404), contenido en el HTML inicial |
| 2 | **Indexable** | ¿Se le permite indexar y sabe cuál es la URL buena? | sin `noindex` accidental, canonical absoluta, una sola versión del sitio (https + con o sin www), sin duplicados |
| 3 | **Entendible** | ¿Sabe de qué trata y quién es? | title y description únicos, un `<h1>`, `lang`, `alt`, JSON-LD de la entidad |
| 4 | **Compartible** | ¿Se ve bien al compartir el link? | Open Graph, Twitter card, `og:image` absoluta |
| 5 | **Descubrible** | ¿Google sabe que existe y le tiene confianza? | Search Console + sitemap enviado, Bing/IndexNow, enlaces entrantes, `sameAs` |

No saltes capas: un JSON-LD perfecto no sirve si `robots.txt` bloquea el sitio o la página tiene `noindex`.

## Flujo de trabajo

1. **Auditar antes de tocar código** — con el script incluido (solo librería estándar, sin navegador):
   ```bash
   python .claude/skills/seo-indexing/scripts/seo_audit.py https://dominio.cl
   python .claude/skills/seo-indexing/scripts/seo_audit.py http://127.0.0.1:8000   # antes de publicar
   ```
   Muestra `[FALTA]` (bloquea la indexación o está roto) y `[AVISO]` (mejora). Guarda la salida como línea base.
2. **Identificar el stack y cómo renderiza.** Server-rendered (Django, Laravel, Rails, Spring+Thymeleaf, Next/Nuxt/Astro con SSR o SSG) → el HTML ya trae todo. **SPA pura** (React/Vue con Vite, CRA) → problema de fondo, ver regla 9. Lee la referencia del stack (tabla abajo).
3. **Implementar capas 1 → 4 en orden**, un commit por capa si el proyecto lo permite: es más fácil de revisar.
4. **Tests automáticos** en el framework del proyecto: `robots.txt` responde 200 `text/plain` con línea `Sitemap:`; el sitemap contiene todas las URLs públicas y ninguna privada; cada vista pública tiene title, description y canonical; el JSON-LD parsea. Los ejemplos por stack están en cada referencia.
5. **Publicar → volver a correr la auditoría contra producción** (el proxy, el CDN y las variables de entorno cambian cosas que en local no se ven) → validar el JSON-LD en el Rich Results Test.
6. **Capa 5, fuera del código**: guiar al usuario en Search Console y en las señales externas → `references/search-console-and-offsite.md`.

## Qué referencia leer

| Stack o tarea | Referencia |
|---|---|
| Qué poner en `<head>`: title, description, canonical, OG, Twitter, JSON-LD por tipo de entidad, hreflang, alt | `references/metadata-and-structured-data.md` (agnóstica, léela siempre junto con la del stack) |
| Django, Flask, FastAPI | `references/python.md` |
| Next.js, React (Vite/SPA), Nuxt/Vue, Astro, SvelteKit, Express, HTML estático | `references/javascript.md` |
| Laravel, WordPress, Spring Boot, Rails, ASP.NET Core | `references/php-java-others.md` |
| Search Console, Bing, IndexNow, Cloudflare, enlaces externos, plazos y cómo medir | `references/search-console-and-offsite.md` |

## Reglas que aplican siempre

1. **`Disallow` en robots.txt no es `noindex`.** Bloquear impide *rastrear*, pero la URL se puede indexar igual (sin contenido) si alguien la enlaza. Para sacar algo del índice: `noindex` (meta o header `X-Robots-Tag`) **y dejar que se rastree**, para que el bot alcance a leerlo.
2. **Nunca listar rutas "secretas" en robots.txt** (admin con URL ofuscada, staging, backups). El archivo es público: listarlas es publicarlas. Esas rutas se protegen con autenticación, no con robots.
3. **Canonical siempre absoluta**: https, dominio canónico, sin parámetros de tracking. Constrúyela desde una constante de configuración (`SITE_URL`) y no desde el header `Host` de la petición.
4. **El sitemap solo lleva URLs canónicas que responden 200**: nada que redirija, tenga `noindex`, esté bloqueado por robots o dé 404. Pon `lastmod` solo si es real; Google ignora `priority` y `changefreq`.
5. **Una sola versión del sitio**: `http→https` y `www↔sin www` con **301**. Muchas veces ya lo resuelve el hosting o el CDN; verifícalo con la auditoría antes de programarlo.
6. **Title y description únicos por página.** Title ~50-60 caracteres, con la marca. Description ~140-160, escrita para humanos (es el texto que sale bajo el resultado; Google a veces la reescribe). `meta keywords` no sirve para nada.
7. **El JSON-LD tiene que coincidir con lo que la página muestra.** Marcar datos que no están visibles es spam de datos estructurados y puede terminar en una acción manual.
8. **Siglas ambiguas o nombres que compiten** (ej. "LMVE" contra otra organización con sigla parecida): declarar la entidad de forma explícita — `WebSite` con `name` y `alternateName` en la home (Google lo usa para el nombre del sitio en los resultados), `Organization` (o el subtipo que corresponda) con `alternateName`, `logo` y `sameAs` a los perfiles oficiales, y el nombre completo junto a la sigla en el title y el `<h1>` de la home.
9. **El contenido crítico va en el HTML inicial.** Googlebot ejecuta JS, pero en una segunda pasada y sin garantía de cuándo; los scrapers de Open Graph (WhatsApp, Facebook, LinkedIn, Slack, X) **nunca** ejecutan JS. En una SPA pura, las meta y el OG que inyecta JS no existen para ellos → SSR, SSG o prerender (ver `references/javascript.md`).
10. **CSP estricta**: un `<script type="application/ld+json">` es un bloque de datos que el navegador no ejecuta; ponerle el nonce igual es inofensivo y evita falsos positivos de herramientas. Escapa siempre `<`, `>` y `&` dentro del JSON (`\u003c`, `\u003e`, `\u0026`): así un `</script>` que venga en un dato no rompe la página ni abre un XSS.
11. **Detrás de un proxy** (Render, Heroku, Railway, Fly, Nginx, Cloudflare) el framework tiene que saber que la petición original era https; si no, genera `http://` en canonical, sitemap y `og:url`. La auditoría lo detecta. Solución por stack en cada referencia; lo más robusto es construir las URLs absolutas desde `SITE_URL`.
12. **Honestidad con los plazos.** Indexar toma de días a un par de semanas tras enviar el sitemap. Posicionar una búsqueda disputada depende sobre todo de enlaces externos y de tiempo. No prometas posiciones.

## Qué no hacer

- Comprar enlaces, granjas de links, texto oculto, keyword stuffing, cloaking (servirle a Googlebot algo distinto que al usuario).
- Marcar `FAQPage` o `HowTo` para "ganar estrellas": desde 2023 Google muestra FAQ solo para sitios de gobierno y salud reconocidos, y retiró HowTo.
- Bloquear CSS o JS en robots.txt: Google los necesita para renderizar.
- Llevar a producción la configuración de staging con `noindex` (clásico: la casilla de WordPress "Disuadir a los motores de búsqueda").
- Poner la ruta del admin en robots.txt (regla 2).

## Verificación rápida sin el script

```bash
curl -sI https://dominio.cl/robots.txt | head -3            # 200 y text/plain
curl -s  https://dominio.cl/sitemap.xml | grep -c "<loc>"   # cuántas URLs lista
curl -s  https://dominio.cl/ | grep -io '<meta name="description"[^>]*>\|<link rel="canonical"[^>]*>\|og:[a-z:]*'
curl -sI https://dominio.cl/pagina | grep -i x-robots-tag   # no debería decir noindex
```

Validadores externos (para el usuario, en el navegador): Rich Results Test (`search.google.com/test/rich-results`), Schema Markup Validator (`validator.schema.org`), Sharing Debugger de Facebook para la vista previa de links (sirve también para refrescar la caché de WhatsApp) y la Inspección de URL de Search Console.
