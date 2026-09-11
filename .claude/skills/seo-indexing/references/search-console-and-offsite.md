# Search Console, Bing, Cloudflare y señales externas (capa 5)

Esto no se programa: se guía al usuario paso a paso. Pídele capturas cuando no sepas qué está viendo en un panel. Nunca le pidas que pegue contraseñas ni claves secretas en el chat (el valor TXT de verificación de Google no es secreto).

**Requisito previo:** la auditoría contra producción sin `[FALTA]` en robots, sitemap, noindex ni canonical. Enviar un sitemap roto a Google solo acumula errores en el informe.

## 1. Google Search Console

### Propiedad y verificación

- **Propiedad de dominio** (recomendada): cubre `http`, `https`, `www` y cualquier subdominio. Se verifica con un registro DNS TXT.
- Propiedad de prefijo de URL: solo esa variante exacta; se verifica con un archivo HTML, una meta o Google Analytics. Úsala solo si no hay acceso al DNS.

**DNS en Cloudflare**: Search Console entrega un valor `google-site-verification=…`. Si aparece la opción de verificar automáticamente con el proveedor, úsala. Si no, en Cloudflare → el dominio → **DNS → Records → Add record**: tipo `TXT`, nombre `@`, contenido el valor completo, TTL `Auto`. Guardar y volver a Search Console → **Verificar**. Suele funcionar en minutos; si falla, esperar un rato y reintentar (propagación).

No borres el TXT después: si desaparece, la propiedad se desverifica.

### Enviar el sitemap

**Sitemaps** → "Añadir un sitemap" → escribir la ruta (`sitemap.xml`, o `sitemap-index.xml` en Astro, `sitemap_index.xml` con Yoast/Rank Math) → **Enviar**. El estado debería pasar a "Correcto" con el número de URLs descubiertas. "No se ha podido obtener" casi siempre es robots.txt, un 404 o un bloqueo del CDN.

### Pedir indexación de lo importante

**Inspección de URLs** → pegar la URL de la home → **Solicitar indexación**. La cuota diaria es limitada: úsala para la home y las 3-5 páginas clave; el resto lo descubre el sitemap.

En la misma pantalla, **"Probar URL publicada" → "Ver página probada"** muestra el HTML y la captura que obtuvo Googlebot. Es la forma definitiva de confirmar que el CDN o el firewall no lo están bloqueando y que el contenido está en el HTML.

### Cómo leer el informe "Páginas" (Indexación → Páginas)

| Estado | Qué significa | Qué hacer |
|---|---|---|
| Descubierta: actualmente sin indexar | Google conoce la URL pero no la ha rastreado | Normal en sitios nuevos. Esperar; mejorar enlaces internos hacia esa página |
| Rastreada: actualmente sin indexar | La leyó y decidió no indexarla por ahora | Contenido escaso, casi duplicado o poco útil. Mejorar esa página |
| Página alternativa con etiqueta canónica adecuada | Es una variante que apunta bien a su canónica | Nada, está correcto |
| Duplicada: Google eligió una canónica diferente | Google no le cree a tu canonical | Revisar duplicados, canonical y enlaces internos |
| Excluida por la etiqueta "noindex" | Tiene noindex | ¿Es a propósito? Si no, sacar el noindex |
| Bloqueada por robots.txt | Disallow la bloquea | ¿Es a propósito? |
| Soft 404 | Parece página vacía o de error con 200 | Devolver 404 real o darle contenido |
| Página con redirección | Es una URL que redirige | Normal para variantes http/www; si es una URL del sitemap, sacarla de ahí |

### Rendimiento

Los datos tardan un par de días en aparecer. Mira **consultas, impresiones, clics y posición media**, y filtra por la marca (nombre completo y sigla por separado). Las impresiones suben antes que los clics: es la primera señal de que el sitio empezó a aparecer.

Chequeo rápido y aproximado de indexación: buscar `site:dominio.cl` en Google.

## 2. Bing Webmaster Tools e IndexNow

- En Bing Webmaster Tools → **Importar desde Google Search Console**: trae la propiedad verificada y el sitemap en un par de clics. El índice de Bing también alimenta a otros buscadores (Yahoo, DuckDuckGo, entre otros).
- **IndexNow**: protocolo con el que el sitio avisa cambios al instante a Bing, Yandex y otros (Google no lo usa). En Cloudflare lo hace **Crawler Hints** sin tocar código (en el panel suele estar en *Caching → Configuration*). Si no hay Cloudflare, existen plugins o se implementa con una clave y un ping.

## 3. Trampas de Cloudflare (y CDN/firewalls en general)

- **Bloqueo por país o reglas WAF propias**: si bloqueaste o desafías países, Googlebot (que rastrea sobre todo desde EE. UU.) puede quedar afuera. Verifícalo con "Probar URL publicada".
- **Bot Fight Mode / bloqueo de bots de IA**: Cloudflare deja pasar a los bots verificados como Googlebot y Bingbot, pero confírmalo igual con la inspección de URL después de activarlos.
- **robots.txt administrado**: Cloudflare puede anteponer directivas propias (por ejemplo, para bots de IA) al robots.txt que sirve tu aplicación. Revisa siempre el que se sirve en vivo (`curl https://dominio.cl/robots.txt`), no solo el del repo.
- **Caché**: si Cloudflare cachea `robots.txt` o `sitemap.xml`, purga la caché después de cambiarlos.
- Las redirecciones `http→https` y `www→sin www` pueden vivir en Cloudflare (Always Use HTTPS + Redirect Rules) o en el hosting; basta con que existan en un lugar y sean 301.

## 4. Señales externas (lo que más pesa en búsquedas disputadas)

En orden de costo/beneficio:

1. **El link oficial en las redes de la organización**: bio de Instagram, "Sitio web" en Facebook, YouTube, LinkedIn. Además de enlace, asocia la cuenta (que ya tiene historia) con el dominio nuevo. Y agrega esos perfiles al `sameAs` del JSON-LD.
2. **Miembros, socios y aliados que enlacen el sitio**: colegios participantes, federaciones, municipalidades, auspiciadores. Un puñado de enlaces desde sitios con autoridad vale más que cualquier ajuste técnico.
3. **Prensa y medios locales**: notas sobre torneos o hitos, con enlace.
4. **Consistencia del nombre**: mismo nombre completo + sigla en todas partes (redes, directorios, prensa, firma de correo).
5. **Perfil de Empresa de Google** (Google Maps): solo si hay un lugar físico al que la gente va o una zona de servicio real. No inventes una dirección.
6. **Wikipedia / Wikidata**: solo si la organización cumple sus criterios de relevancia con fuentes independientes, y sin que la escriba alguien de la propia organización (conflicto de interés). Si existe, va al `sameAs`.

**No**: comprar enlaces, intercambios masivos, directorios spam, comentarios con links. Google los detecta y pueden hundir el sitio.

## 5. Plazos realistas (para decírselos al usuario)

| Momento | Qué esperar |
|---|---|
| Día 0 | Deploy, verificación, sitemap enviado, indexación de la home solicitada |
| Primeros días a 2 semanas | La home aparece en `site:dominio.cl`; empiezan las impresiones por el nombre completo |
| Semanas 2-6 | El resto de las páginas se indexa; el nombre completo aparece primero |
| Meses | Ganar una sigla o una palabra disputada; depende casi todo de los enlaces externos |

Si después de 2-3 semanas la home no está indexada: inspección de URL (¿bloqueada?, ¿noindex?, ¿canonical rara?) y el informe "Páginas".

## 6. Checklist de cierre

- [ ] Auditoría contra producción sin `[FALTA]`
- [ ] Rich Results Test del JSON-LD de la home, sin errores
- [ ] Vista previa del link revisada en el Sharing Debugger (y en WhatsApp)
- [ ] Search Console: propiedad de dominio verificada, sitemap "Correcto", indexación de la home solicitada
- [ ] Bing Webmaster Tools importado desde Search Console
- [ ] Link al sitio en las redes oficiales y en `sameAs`
- [ ] Revisión en 1-2 semanas: informe "Páginas" y "Rendimiento"
