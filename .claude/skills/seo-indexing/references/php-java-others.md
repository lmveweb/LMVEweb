# PHP, Java y otros: Laravel, WordPress, Spring Boot, Rails, ASP.NET Core

Todos renderizan en el servidor. En cada uno hay que resolver lo mismo: meta por página desde el layout, canonical absoluta, `robots.txt`, `sitemap.xml`, JSON-LD escapado y que el framework sepa que detrás del proxy la petición era https.

---

## Laravel

**Proxy y URL base**

```php
// bootstrap/app.php (Laravel 11+). En ≤10: App\Http\Middleware\TrustProxies::$proxies
->withMiddleware(function (Middleware $middleware) {
    $middleware->trustProxies(at: '*');   // '*' solo si la app no es accesible salvo por el proxy
})
```

`APP_URL=https://dominio.cl` en `.env` y, si hace falta, `URL::forceScheme('https')` en `AppServiceProvider::boot()` para producción.

**Layout Blade** (a diferencia de Django, `@yield` sí se puede repetir, así que el mismo título sirve para `og:title`):

```blade
<title>@yield('title', 'Nombre completo (SIGLA)')</title>
<meta name="description" content="@yield('description', 'Descripción por defecto')">
<link rel="canonical" href="{{ url()->current() }}">   {{-- sin query string --}}
<meta property="og:title" content="@yield('title', 'Nombre completo (SIGLA)')">
<meta property="og:description" content="@yield('description', 'Descripción por defecto')">
<meta property="og:url" content="{{ url()->current() }}">
<meta property="og:image" content="{{ asset('img/og.jpg') }}">
<meta name="twitter:card" content="summary_large_image">
@isset($jsonLd)
<script type="application/ld+json">@json($jsonLd)</script>
@endisset
```

`@json` usa `JSON_HEX_TAG | JSON_HEX_AMP | …` por defecto, así que ya escapa `<`, `>` y `&`. No lo cambies por `{!! json_encode(...) !!}` sin esas banderas.

**Sitemap** con `spatie/laravel-sitemap`:

```php
use Spatie\Sitemap\Sitemap;
use Spatie\Sitemap\Tags\Url;

Route::get('/sitemap.xml', fn () => Sitemap::create()
    ->add(Url::create('/'))
    ->add(Url::create('/historia'))
    ->add(Noticia::publicadas()->get())   // si el modelo implementa Sitemapable
);
```

O generarlo a archivo (`->writeToFile(public_path('sitemap.xml'))`) desde un comando programado si el sitio es grande.

**robots.txt**: Laravel trae `public/robots.txt` con `Disallow:` vacío (permite todo). Solo agrégale `Sitemap: https://dominio.cl/sitemap.xml`. 404 real: `abort(404)` o `firstOrFail()`.

---

## WordPress

No reinventes: el núcleo y un plugin de SEO resuelven casi todo. Lo que sí hay que revisar:

- **Ajustes → Lectura → "Disuadir a los motores de búsqueda de indexar este sitio" desmarcado** en producción. Es la causa número uno de "WordPress no aparece en Google": se marca en staging y se migra así.
- **Ajustes → Enlaces permanentes → "Nombre de la entrada"** (URLs legibles).
- Sitemap: WordPress 5.5+ genera `/wp-sitemap.xml`. Yoast o Rank Math lo reemplazan por `/sitemap_index.xml` y agregan meta, OG y schema. **Usa un solo plugin de SEO**, y no escribas meta a mano en el tema si el plugin está activo (quedan duplicadas).
- En el plugin, completa el tipo de entidad (Organización), el nombre, el nombre alternativo/sigla, el logo y los perfiles sociales: eso produce el JSON-LD de la regla de siglas ambiguas.
- Detrás de un proxy o CDN que termina el TLS, en `wp-config.php`:

```php
if (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https') {
    $_SERVER['HTTPS'] = 'on';
}
```

y `WP_HOME` / `WP_SITEURL` con `https://`.

---

## Spring Boot (con Thymeleaf)

```properties
# application.properties
server.forward-headers-strategy=framework
app.site-url=https://dominio.cl
```

```java
@RestController
class SeoController {

    @Value("${app.site-url}")
    private String site;

    @GetMapping(value = "/robots.txt", produces = MediaType.TEXT_PLAIN_VALUE)
    String robots() {
        return String.join("\n", "User-agent: *", "Allow: /", "", "Sitemap: " + site + "/sitemap.xml") + "\n";
    }

    @GetMapping(value = "/sitemap.xml", produces = MediaType.APPLICATION_XML_VALUE)
    String sitemap() {
        String urls = Stream.of("/", "/historia", "/contacto")
                .map(r -> "<url><loc>" + site + r + "</loc></url>")
                .collect(Collectors.joining());
        return "<?xml version='1.0' encoding='UTF-8'?>"
                + "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>" + urls + "</urlset>";
    }
}
```

Si hay Spring Security, permite `/robots.txt` y `/sitemap.xml` sin autenticación.

**Canonical en Thymeleaf**: desde Thymeleaf 3.1 (Spring Boot 3) ya no existen `#request` ni `#session` en las expresiones, así que la URL se pasa al modelo:

```java
@ControllerAdvice
class SeoAdvice {
    @Value("${app.site-url}")
    private String site;

    @ModelAttribute("canonical")
    String canonical(HttpServletRequest request) {
        return site + request.getRequestURI();
    }
}
```

```html
<!-- templates/fragments/seo.html -->
<th:block th:fragment="seo(titulo, descripcion)">
  <title th:text="${titulo}">SIGLA</title>
  <meta name="description" th:content="${descripcion}">
  <link rel="canonical" th:href="${canonical}">
  <meta property="og:title" th:content="${titulo}">
  <meta property="og:description" th:content="${descripcion}">
  <meta property="og:url" th:content="${canonical}">
  <meta name="twitter:card" content="summary_large_image">
  <script type="application/ld+json" th:if="${jsonLd}" th:utext="${jsonLd}"></script>
</th:block>

<!-- en cada página -->
<head><th:block th:replace="~{fragments/seo :: seo('Historia | SIGLA', 'Descripción…')}"></th:block></head>
```

`jsonLd` se arma con Jackson en el controlador y se escapa antes de pasarlo (`th:utext` no escapa):

```java
String jsonLd = mapper.writeValueAsString(datos)
        .replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026");
```

---

## Ruby on Rails

- `config.force_ssl = true` en producción (también interpreta `X-Forwarded-Proto`).
- Meta con la gema `meta-tags`: `set_meta_tags title: 'Historia', description: '…', canonical: request.base_url + request.path` en el controlador y `<%= display_meta_tags site: 'SIGLA', reverse: true %>` en el layout.
- Sitemap con la gema `sitemap_generator` (`config/sitemap.rb` con `default_host = 'https://dominio.cl'`, regenerado con `rails sitemap:refresh` en el deploy o programado).
- JSON-LD: `<script type="application/ld+json"><%= json_escape(datos.to_json).html_safe %></script>`.
- `public/robots.txt` con la línea `Sitemap:`.

---

## ASP.NET Core

- Detrás de un proxy: `app.UseForwardedHeaders()` con `ForwardedHeadersOptions` que incluya `XForwardedProto`, y registra la IP o red del proxy como conocida (por defecto solo confía en localhost).
- robots y sitemap como endpoints mínimos:

```csharp
var site = builder.Configuration["SiteUrl"];   // https://dominio.cl

app.MapGet("/robots.txt", () =>
    Results.Text($"User-agent: *\nAllow: /\n\nSitemap: {site}/sitemap.xml\n", "text/plain"));

app.MapGet("/sitemap.xml", () =>
{
    var urls = string.Concat(new[] { "/", "/historia", "/contacto" }
        .Select(r => $"<url><loc>{site}{r}</loc></url>"));
    return Results.Text(
        $"<?xml version='1.0' encoding='UTF-8'?><urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>{urls}</urlset>",
        "application/xml");
});
```

- Razor: `<title>@ViewData["Title"] | SIGLA</title>` y `@RenderSection("Meta", required: false)` en `_Layout.cshtml`; cada vista llena la sección.
- JSON-LD: `@Html.Raw(JsonSerializer.Serialize(datos))`. El encoder por defecto de `System.Text.Json` ya escapa `<`, `>` y `&`; **no** uses `JavaScriptEncoder.UnsafeRelaxedJsonEscaping` acá.
