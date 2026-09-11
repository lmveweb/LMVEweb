# JavaScript: Next.js, React (Vite/SPA), Vue/Nuxt, Astro, SvelteKit, Express, HTML estático

La primera pregunta en JS siempre es **¿el HTML que sale del servidor ya trae el contenido y las meta?** Compruébalo con `curl -s https://dominio.cl/ruta | grep -i '<title>\|og:\|description'` (o con la auditoría de la skill, que tampoco ejecuta JS).

| Cómo renderiza | ¿Scrapers de OG ven las meta? | ¿Google? | Qué hacer |
|---|---|---|---|
| SSR / SSG (Next, Nuxt, Astro, SvelteKit, Remix/React Router framework) | Sí | Sí | Solo producir bien las meta |
| SPA pura (Vite + React/Vue, CRA) | **No** | Tarde y sin garantía | Prerender/SSG o migrar a un framework con SSR; mínimo: meta estáticas en `index.html` |

Todos los ejemplos escapan `<` al serializar JSON-LD (`.replace(/</g, '\\u003c')`): sin eso, un `</script>` dentro de un dato corta el bloque.

---

## Next.js (App Router)

### Metadatos globales

```tsx
// app/layout.tsx
import type { Metadata } from 'next'

export const openGraphBase = {
  type: 'website',
  siteName: 'SIGLA',
  locale: 'es_CL',
  images: [{ url: '/og.jpg', width: 1200, height: 630, alt: 'Descripción de la imagen' }],
} as const

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? 'https://dominio.cl'),
  title: { default: 'Nombre completo (SIGLA)', template: '%s | SIGLA' },
  description: 'Descripción general, ~150 caracteres.',
  openGraph: openGraphBase,
  twitter: { card: 'summary_large_image' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="es-CL"><body>{children}</body></html>
}
```

- `metadataBase` resuelve todas las URLs relativas (`/og.jpg`, canonical) a absolutas, sin depender del proxy.
- **No pongas `alternates.canonical` en el layout raíz**: se hereda a todas las páginas que no la definan y todas terminan canonicalizadas a la home. La canonical va en cada página.
- La fusión de `metadata` es **superficial**: si una página define `openGraph`, reemplaza el del layout completo (se pierden las imágenes). Por eso `openGraphBase` se exporta y se esparce.

### Por página

```tsx
// app/historia/page.tsx
import type { Metadata } from 'next'
import { openGraphBase } from '../layout'

export const metadata: Metadata = {
  title: 'Historia',                               // → "Historia | SIGLA"
  description: '…',
  alternates: { canonical: '/historia' },
  openGraph: { ...openGraphBase, title: 'Historia de la SIGLA', url: '/historia' },
}
```

Rutas dinámicas (Next 15+: `params` es una promesa):

```tsx
export async function generateMetadata(
  { params }: { params: Promise<{ slug: string }> },
): Promise<Metadata> {
  const { slug } = await params
  const noticia = await obtenerNoticia(slug)
  if (!noticia) return { robots: { index: false } }
  return {
    title: noticia.titulo,
    description: noticia.resumen,
    alternates: { canonical: `/noticias/${slug}` },
    openGraph: { ...openGraphBase, type: 'article', url: `/noticias/${slug}`,
                 images: [{ url: noticia.imagen, width: 1200, height: 630 }] },
  }
}
```

Y en la página, `notFound()` de `next/navigation` cuando no existe: devuelve un 404 real.

### JSON-LD

```tsx
// app/page.tsx (home)
export default function Home() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@graph': [
      { '@type': 'WebSite', '@id': 'https://dominio.cl/#sitio', url: 'https://dominio.cl/',
        name: 'Nombre completo', alternateName: ['SIGLA'] },
      { '@type': 'SportsOrganization', '@id': 'https://dominio.cl/#organizacion',
        name: 'Nombre completo', alternateName: 'SIGLA', url: 'https://dominio.cl/',
        logo: 'https://dominio.cl/logo-512.png', sameAs: ['https://www.instagram.com/cuenta/'] },
    ],
  }
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd).replace(/</g, '\\u003c') }}
      />
      {/* … */}
    </>
  )
}
```

### sitemap y robots

```ts
// app/sitemap.ts
import type { MetadataRoute } from 'next'

const SITE = 'https://dominio.cl'

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const estaticas = ['', '/historia', '/contacto'].map((r) => ({ url: `${SITE}${r}` }))
  const noticias = (await listarNoticiasPublicadas()).map((n) => ({
    url: `${SITE}/noticias/${n.slug}`,
    lastModified: n.actualizada,          // fecha real, no new Date()
  }))
  return [...estaticas, ...noticias]
}
```

```ts
// app/robots.ts
import type { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: { userAgent: '*', allow: '/' },
    sitemap: 'https://dominio.cl/sitemap.xml',
  }
}
```

**Pages Router** (proyectos viejos): `next/head` en cada página con `<title>`, `<meta>` y `<link rel="canonical">`; sitemap y robots con el paquete `next-sitemap` en `postbuild`, o archivos en `public/`.

---

## React con Vite (SPA) y otras SPA

El problema de fondo: el servidor entrega un `index.html` casi vacío y todo lo demás lo arma el navegador.

**Opciones, de mejor a peor:**

1. **Renderizar en el servidor o en el build.** React Router v7 en modo framework puede prerenderizar rutas (`prerender` en `react-router.config.ts`) o hacer SSR; también se puede migrar a Next o Astro. Para Vue con Vite existe `vite-ssg`. Esto resuelve Google **y** los scrapers de OG.
2. **Mínimo viable si no se puede cambiar la arquitectura:**
   - Meta generales **estáticas** en `index.html` (title, description, OG con imagen absoluta, twitter:card). Todos los links compartidos mostrarán esa tarjeta.
   - Meta por ruta en el cliente para Google: en **React 19** puedes renderizar `<title>`, `<meta>` y `<link>` dentro de cualquier componente y React los sube al `<head>`. En React ≤18, `react-helmet-async`. En Vue, `@unhead/vue` (`useHead`, `useSeoMeta`).
   - `robots.txt` en `public/` y un `sitemap.xml` generado en el build:

```js
// scripts/sitemap.mjs  →  "build": "vite build && node scripts/sitemap.mjs"
import { writeFileSync } from 'node:fs'

const SITE = 'https://dominio.cl'
const rutas = ['/', '/historia', '/contacto']

const urls = rutas.map((r) => `  <url><loc>${SITE}${r}</loc></url>`).join('\n')
writeFileSync('dist/sitemap.xml',
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`)
```

**Soft 404 en SPA**: el hosting suele devolver `index.html` con **200** para cualquier ruta, así que las URLs inexistentes parecen páginas válidas. Lo que recomienda Google: en el componente "no encontrado", agregar `<meta name="robots" content="noindex">` por JS, o redirigir por JS a una URL que el servidor sí responda con 404. La auditoría de la skill detecta el soft 404.

---

## Nuxt 3 (Vue)

```ts
// nuxt.config.ts
export default defineNuxtConfig({
  modules: ['@nuxtjs/sitemap', '@nuxtjs/robots'],   // parte de "Nuxt SEO"
  site: { url: 'https://dominio.cl', name: 'SIGLA' },
  app: { head: { htmlAttrs: { lang: 'es-CL' } } },
})
```

```vue
<!-- pages/historia.vue -->
<script setup lang="ts">
const url = 'https://dominio.cl/historia'
useSeoMeta({
  title: 'Historia | SIGLA',
  description: '…',
  ogTitle: 'Historia de la SIGLA',
  ogDescription: '…',
  ogUrl: url,
  ogImage: 'https://dominio.cl/og.jpg',
  twitterCard: 'summary_large_image',
})
useHead({ link: [{ rel: 'canonical', href: url }] })
</script>
```

JSON-LD: el módulo `nuxt-schema-org` (`useSchemaOrg`) o `useHead({ script: [{ type: 'application/ld+json', innerHTML: JSON.stringify(datos).replace(/</g, '\\u003c') }] })`. Deja `ssr: true` (el default); con `ssr: false` vuelves al problema de la SPA.

---

## Astro

```js
// astro.config.mjs
import { defineConfig } from 'astro/config'
import sitemap from '@astrojs/sitemap'

export default defineConfig({
  site: 'https://dominio.cl',        // obligatorio para el sitemap y las URLs absolutas
  integrations: [sitemap()],
})
```

`@astrojs/sitemap` genera **`/sitemap-index.xml`** (no `/sitemap.xml`): apunta ahí desde robots.txt y en Search Console.

```astro
---
// src/layouts/Base.astro
const { title, description, jsonLd } = Astro.props
const canonical = new URL(Astro.url.pathname, Astro.site)
const ogImage = new URL('/og.jpg', Astro.site)
---
<html lang="es-CL">
  <head>
    <title>{title}</title>
    <meta name="description" content={description} />
    <link rel="canonical" href={canonical} />
    <meta property="og:type" content="website" />
    <meta property="og:title" content={title} />
    <meta property="og:description" content={description} />
    <meta property="og:url" content={canonical} />
    <meta property="og:image" content={ogImage} />
    <meta name="twitter:card" content="summary_large_image" />
    {jsonLd && <script type="application/ld+json" set:html={JSON.stringify(jsonLd).replace(/</g, '\\u003c')} />}
  </head>
  <body><slot /></body>
</html>
```

```text
# public/robots.txt
User-agent: *
Allow: /

Sitemap: https://dominio.cl/sitemap-index.xml
```

---

## SvelteKit

```svelte
<!-- src/routes/historia/+page.svelte -->
<script>
  import { page } from '$app/state'   // antes de SvelteKit 2.12: $app/stores y $page
  const titulo = 'Historia | SIGLA'
</script>

<svelte:head>
  <title>{titulo}</title>
  <meta name="description" content="…" />
  <link rel="canonical" href={`https://dominio.cl${page.url.pathname}`} />
  <meta property="og:title" content={titulo} />
  <meta property="og:image" content="https://dominio.cl/og.jpg" />
</svelte:head>
```

```js
// src/routes/sitemap.xml/+server.js
const SITE = 'https://dominio.cl'
const rutas = ['/', '/historia', '/contacto']

export const prerender = true

export function GET() {
  const urls = rutas.map((r) => `<url><loc>${SITE}${r}</loc></url>`).join('')
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`,
    { headers: { 'Content-Type': 'application/xml' } },
  )
}
```

`robots.txt` en `static/`. Para errores, `error(404, …)` de `@sveltejs/kit` en `load` devuelve un 404 real.

---

## Express (con EJS, Pug, Handlebars…)

```js
const SITE = process.env.SITE_URL ?? 'https://dominio.cl'
app.set('trust proxy', 1)   // detrás de UN proxy: req.protocol pasa a ser https

app.get('/robots.txt', (req, res) => {
  res.type('text/plain').send(`User-agent: *\nAllow: /\n\nSitemap: ${SITE}/sitemap.xml\n`)
})

app.get('/sitemap.xml', (req, res) => {
  const rutas = ['/', '/historia', '/contacto']
  const urls = rutas.map((r) => `<url><loc>${SITE}${r}</loc></url>`).join('')
  res.type('application/xml').send(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`)
})

// Meta: pasar { title, description, canonical: SITE + req.path } a res.render()
// y usarlas en el layout. 404 real: res.status(404).render('404') al final.
```

---

## HTML estático (o generadores: Eleventy, Hugo, Jekyll)

- `<head>` completo a mano en cada página (ver `metadata-and-structured-data.md`).
- `robots.txt` y `sitemap.xml` como archivos en la raíz. Con un generador, usa su plugin o plantilla de sitemap en vez de mantenerlo a mano.
- Configura el hosting para que las rutas inexistentes den 404 con una página `404.html` (Netlify, Vercel, GitHub Pages y Cloudflare Pages lo hacen si el archivo existe).
