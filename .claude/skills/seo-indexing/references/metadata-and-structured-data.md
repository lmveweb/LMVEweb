# Metadatos y datos estructurados (agnóstico del framework)

Qué debe terminar en el HTML de cada página, sin importar cómo se genere. Cada referencia de stack explica *cómo* producir esto en ese framework.

## El `<head>` completo de referencia

```html
<!doctype html>
<html lang="es-CL">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <title>Historia | LMVE</title>
  <meta name="description" content="Desde 1987, la Liga Metropolitana de Voleibol Escolar reúne a colegios de Santiago. Conoce su historia, épocas y protagonistas.">
  <link rel="canonical" href="https://dominio.cl/historia/">

  <!-- Open Graph: WhatsApp, Facebook, LinkedIn, Slack, Discord, iMessage -->
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="LMVE">
  <meta property="og:locale" content="es_CL">
  <meta property="og:title" content="Historia de la LMVE">
  <meta property="og:description" content="Desde 1987, la Liga reúne a colegios de Santiago…">
  <meta property="og:url" content="https://dominio.cl/historia/">
  <meta property="og:image" content="https://dominio.cl/static/img/og-historia.jpg">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Equipo de la Liga en 1987">

  <!-- X/Twitter: usa og:title/description/image como respaldo; la card sí hay que declararla -->
  <meta name="twitter:card" content="summary_large_image">

  <!-- JSON-LD: ver más abajo -->
</head>
```

Si la página **no debe indexarse** (resultados de búsqueda interna, confirmaciones, staging): `<meta name="robots" content="noindex, follow">`, no la listes en el sitemap y **no** la bloquees en robots.txt (el bot tiene que poder leer el `noindex`).

## Title

- Único por página; ~50-60 caracteres (Google trunca por píxeles, ~600 px).
- Home: `Nombre completo (SIGLA) | propuesta corta` o `SIGLA | Nombre completo`. Si la sigla es ambigua, **las dos cosas juntas** en la home.
- Internas: `Tema de la página | Marca`. La marca al final, lo específico al principio.
- Nada de listas de palabras clave separadas por comas.

## Meta description

- Única por página; ~140-160 caracteres; frase natural que invite al clic y diga qué hay en la página.
- Google la reescribe cuando cree que otra frase de la página responde mejor la búsqueda: normal, no es un error.
- Si no hay nada bueno que decir de una página, mejor preguntarse si debería indexarse.

## Canonical

- Absoluta, `https://`, dominio canónico, con la barra final **igual** que la URL real (en Django suele ser con `/`).
- Sin parámetros de tracking (`?utm_…`, `?fbclid=`). Si la página pagina (`?page=2`), cada página se canonicaliza a sí misma, no a la página 1.
- Una por página. Nunca apuntar todas las páginas a la home.

## Open Graph y la imagen para compartir

- `og:image` **absoluta**. Con estáticos con hash (WhiteNoise, Vite, Next) la URL cambia cuando cambia la imagen, lo que obliga a los scrapers a pedirla de nuevo: bien.
- 1200×630 (proporción 1.91:1), JPG o PNG. En la práctica WhatsApp muestra la vista previa de forma más confiable con imágenes livianas (~300 KB o menos).
- Una imagen genérica del sitio sirve para todas las páginas; una propia por sección es mejor.
- Los scrapers cachean agresivo. Para forzar una nueva lectura: Sharing Debugger de Facebook ("Scrape Again"); WhatsApp se actualiza con eso o con el tiempo.
- `og:title` puede ser más conversacional que el `<title>` (sin el `| Marca`).

## Headings, idioma, imágenes

- Un `<h1>` por página, que diga lo mismo que el title en otras palabras. Luego `h2`/`h3` en orden, sin saltarse niveles por estética (para eso está el CSS).
- `<html lang="es-CL">` (o el que corresponda).
- `alt` descriptivo en imágenes con contenido; `alt=""` en imágenes decorativas (no omitas el atributo). Es accesibilidad y además SEO de imágenes.
- Nombres de archivo con sentido (`final-2024-colegio-x.jpg` > `IMG_4412.jpg`).

## Multilingüe (solo si aplica)

Cada versión de idioma enlaza a todas las demás y a sí misma, en todas las páginas (tiene que ser recíproco):

```html
<link rel="alternate" hreflang="es-CL" href="https://dominio.cl/historia/">
<link rel="alternate" hreflang="en" href="https://dominio.cl/en/history/">
<link rel="alternate" hreflang="x-default" href="https://dominio.cl/historia/">
```

## Datos estructurados (JSON-LD)

Un bloque `<script type="application/ld+json">` en el `<head>` o en el `<body>`. Reglas:

- Tiene que describir lo que **la página muestra**. Nada inventado ni oculto.
- Usa `@id` para enlazar entidades entre bloques y páginas (`"@id": "https://dominio.cl/#organizacion"`).
- Escapa `<`, `>` y `&` al serializar (cada referencia de stack trae el helper). Sin eso, un `</script>` dentro de un dato cierra el bloque antes de tiempo.
- Valida en el Rich Results Test (lo que Google usa) y en validator.schema.org (sintaxis general).

### Home: `WebSite` + la organización, en un `@graph`

```json
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://dominio.cl/#sitio",
      "url": "https://dominio.cl/",
      "name": "Liga Metropolitana de Voleibol Escolar",
      "alternateName": ["LMVE", "Liga Metropolitana de Vóleibol Escolar"],
      "inLanguage": "es-CL",
      "publisher": { "@id": "https://dominio.cl/#organizacion" }
    },
    {
      "@type": "SportsOrganization",
      "@id": "https://dominio.cl/#organizacion",
      "name": "Liga Metropolitana de Voleibol Escolar",
      "alternateName": "LMVE",
      "url": "https://dominio.cl/",
      "logo": "https://dominio.cl/static/img/logo-512.png",
      "description": "Liga de voleibol escolar de la Región Metropolitana, fundada en 1987.",
      "foundingDate": "1987",
      "sport": "Voleibol",
      "areaServed": { "@type": "AdministrativeArea", "name": "Región Metropolitana de Santiago" },
      "address": {
        "@type": "PostalAddress",
        "addressLocality": "Santiago",
        "addressRegion": "Región Metropolitana",
        "addressCountry": "CL"
      },
      "email": "contacto@ejemplo.cl",
      "sameAs": [
        "https://www.instagram.com/cuenta_oficial/"
      ]
    }
  ]
}
```

- `WebSite.name` + `alternateName` en la home es lo que Google usa para el **nombre del sitio** que aparece sobre el resultado. Es la herramienta principal cuando la sigla se confunde con otra.
- `logo`: cuadrado, mínimo 112×112, URL estable y rastreable.
- `sameAs`: solo perfiles **oficiales** que la organización controla (Instagram, Facebook, YouTube, LinkedIn, Wikipedia/Wikidata si existen).

### Qué tipo de organización usar

| Caso | `@type` |
|---|---|
| Liga, club, federación deportiva | `SportsOrganization` (o `SportsTeam` para un equipo) |
| Colegio, universidad, instituto | `EducationalOrganization` / `School` / `CollegeOrUniversity` |
| ONG, fundación | `NGO` |
| Negocio con local al que va gente o que atiende una zona | `LocalBusiness` o su subtipo (`Restaurant`, `Dentist`, `Store`…) + `openingHoursSpecification`, `geo`, `telephone`. Complementa, no reemplaza, el Perfil de Empresa de Google |
| Empresa sin local de atención | `Organization` / `Corporation` |
| Sitio personal o portafolio | `Person` + `WebSite` |

### Otros tipos útiles (solo si la página realmente lo es)

- **`BreadcrumbList`**: sitios con jerarquía (tienda › categoría › producto). Muestra la ruta en el resultado.
- **`Event`**: una página por evento (partido final, torneo, inscripción) con `name`, `startDate` (ISO 8601 con zona horaria), `location` (`Place` con `address`), `organizer`, `eventStatus`, `eventAttendanceMode`. Elegible para resultados de eventos.
- **`Article` / `NewsArticle` / `BlogPosting`**: noticias y blog, con `headline`, `datePublished`, `dateModified`, `author`, `image`.
- **`Product`** + `Offer`: e-commerce, con `price`, `priceCurrency`, `availability`. Si hay reseñas, que sean reales y visibles en la página.
- **`FAQPage` / `HowTo`**: no los uses esperando rich results (ver "Qué no hacer" en SKILL.md).

```json
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    { "@type": "ListItem", "position": 1, "name": "Inicio", "item": "https://dominio.cl/" },
    { "@type": "ListItem", "position": 2, "name": "Historia", "item": "https://dominio.cl/historia/" }
  ]
}
```

## robots.txt de referencia

```text
User-agent: *
Allow: /

Sitemap: https://dominio.cl/sitemap.xml
```

Eso es todo lo que necesita un sitio chico. Agrega `Disallow:` solo para zonas **públicas** que no aportan (búsqueda interna con parámetros, carrito) y nunca para rutas que quieras mantener en secreto. Si decides bloquear bots de IA, hazlo con líneas por `User-agent` específicos (p. ej. `GPTBot`); no toques `Googlebot` ni `Bingbot`.

## sitemap.xml de referencia

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://dominio.cl/</loc>
    <lastmod>2026-09-01</lastmod>
  </url>
  <url>
    <loc>https://dominio.cl/historia/</loc>
  </url>
</urlset>
```

- Hasta 50.000 URLs o 50 MB por archivo; más que eso → sitemap index.
- Solo URLs finales 200, canónicas, indexables. La auditoría de la skill lo verifica.
- `lastmod` solo si refleja un cambio real de contenido (una fecha que cambia en cada deploy le enseña a Google a ignorarla).
