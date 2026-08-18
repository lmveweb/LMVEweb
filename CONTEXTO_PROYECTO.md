# LMVEweb — Contexto completo del proyecto

> Documento de referencia pensado para subir a Claude Projects. Es autocontenido: no asume que quien lo lea tuvo acceso a ninguna conversación previa sobre este proyecto.
>
> Última actualización: 17 de agosto de 2026.

---

# PARTE 1 — Ficha técnica

## 1.1 Qué es

Sitio web institucional de la **Liga Metropolitana de Voleibol Escolar (LMVE)**, fundada en 1987, Región Metropolitana, Chile. Django monolítico, server-rendered (sin frontend framework, sin API separada). Seis vistas públicas: Inicio, Historia, Sobre la LMVE, Multimedia, Contacto (con formulario funcional que guarda en base de datos y envía correo), e Impacto (página de material de auspicio, deliberadamente fuera del menú, pensada para enviarse por link directo a marcas).

Aún no está desplegado. Todo el desarrollo ocurre en local; el hosting elegido es **Render**, con PostgreSQL administrado.

## 1.2 Stack tecnológico

| Componente | Elección | Versión |
|---|---|---|
| Lenguaje | Python | 3.14 |
| Framework | Django | 6.0.5 |
| Servidor WSGI (producción) | Gunicorn | 26.0.0 |
| Estáticos | WhiteNoise (`CompressedManifestStaticFilesStorage`) | 6.12.0 |
| Base de datos (local) | SQLite | — |
| Base de datos (producción) | PostgreSQL administrado (Render) | vía `dj-database-url` 3.1.2 |
| Driver Postgres | psycopg2-binary | 2.9.12 |
| Variables de entorno | python-dotenv | 1.2.2 |
| Rate limiting | django-ratelimit | 4.1.0 |
| CSP (Content-Security-Policy) | django-csp | 4.0 |
| Monitoreo de errores (opcional) | sentry-sdk | 2.67.1 |
| Gráfico 3D | Three.js r128 (vía CDN cdnjs) + script propio | — |
| Tipografía de display | Barlow Condensed (SIL OFL, auto-hospedada) | — |
| CI | GitHub Actions | — |

`requirements.txt` completo:
```
Django==6.0.5
whitenoise==6.12.0
dj-database-url==3.1.2
python-dotenv==1.2.2
gunicorn==26.0.0
psycopg2-binary==2.9.12
django-ratelimit==4.1.0
django-csp==4.0
sentry-sdk==2.67.1
```

## 1.3 Estructura del proyecto

```
LMVEweb/                       ← proyecto Django (config global)
  settings.py                  ← toda la config vive acá, ver 1.8/1.11
  urls.py                      ← monta /admin/ (ruta configurable) + core.urls
  wsgi.py                      ← LMVEweb.wsgi:application (usado por gunicorn)
  asgi.py                      ← existe pero no se usa (no hay nada async)

core/                          ← única app Django del proyecto
  models.py                    ← un solo modelo: MensajePatrocinio
  views.py                     ← 6 vistas, todas function-based
  urls.py                      ← rutas de la app
  admin.py                     ← registro de MensajePatrocinio en /admin/
  tests.py                     ← 5 tests sobre la vista contacto()
  migrations/0001_initial.py   ← única migración

  templates/core/
    base.html                  ← layout compartido: header, footer, paleta
                                  CSS, tipografía, menú móvil. Todo lo
                                  visual global vive acá.
    home.html                  ← Inicio
    proyecto.html               ← Historia (url /historia/)
    sobre.html                  ← Sobre la LMVE (Visión/Misión)
    archivo.html                ← Multimedia (galería)
    contacto.html                ← Formulario de auspicio
    impacto.html                 ← Material de auspicio (fuera del menú)

  static/core/
    fonts/                      ← Barlow Condensed (.woff2 x5) + OFL.txt
    img/
      logo-*.png                ← 6 variantes del isotipo LMVE
      molten.svg                ← logo del patrocinador (editado, ver 2.1)
      fotos/                    ← 69 fotos de la galería, ~17 MB sin comprimir
      colegios/                 ← 44 logos de colegios (carrusel de Inicio)
    js/pelota3d.js              ← pelota de vóleibol 3D generada por código
                                   (Three.js), reutilizada en Historia y
                                   Sobre la LMVE
    video/hero-copa.mp4         ← video de fondo del hero de Inicio

.github/workflows/ci.yml       ← tests + check --deploy en cada push/PR
Procfile                       ← release (migrate + createcachetable) + web (gunicorn)
build.sh                       ← Build Command de Render: pip install + collectstatic
requirements.txt
.env.example                   ← plantilla de variables de entorno (se commitea)
.env                           ← valores reales locales (gitignored)
db.sqlite3                     ← base de datos local (gitignored)
README.md
DEPLOY_PLAN_TECHNICAL.md       ← plan de despliegue, versión técnica
DEPLOY_PLAN_PARA_DIRIGENTES.md ← mismo plan, versión no técnica para la Junta
```

## 1.4 Modelo de datos

Un solo modelo en todo el proyecto:

```python
class MensajePatrocinio(models.Model):
    class NivelInteres(models.TextChoices):
        NAMING = 'naming', 'Main Sponsor (Naming Rights)'
        APPAREL = 'apparel', 'Indumentaria y Equipamiento'
        DIGITAL = 'digital', 'Digital & Streaming Partner'
        OTHER = 'other', 'Activaciones y BTL en recinto'

    empresa = models.CharField('Empresa o Marca', max_length=200)
    contacto = models.CharField('Persona de Contacto', max_length=200)
    email = models.EmailField('Correo Electrónico')
    interes = models.CharField('Nivel de Interés', max_length=20, choices=NivelInteres.choices)
    mensaje = models.TextField('Mensaje Adicional', blank=True)
    creado = models.DateTimeField('Fecha de Envío', auto_now_add=True)
```

Cada fila es un envío del formulario de Contacto. Se administra desde `/admin/` (list_display con empresa/contacto/email/interés/fecha, filtros por interés y fecha, búsqueda por empresa/contacto/email).

## 1.5 Rutas

| Ruta | Vista | Template | Qué hace |
|---|---|---|---|
| `/` | `home` | `home.html` | Hero con video, cifras institucionales, embeds de Instagram, carrusel de colegios |
| `/historia/` | `proyecto` | `proyecto.html` | Timeline por décadas (tabs), pelota 3D |
| `/sobre/` | `sobre` | `sobre.html` | Visión y Misión, con efecto de "brochazo de destacador" en los títulos |
| `/multimedia/` | `archivo` | `archivo.html` | Galería de fotos con lightbox y lazy-load |
| `/contacto/` | `contacto` | `contacto.html` | Formulario de auspicio (GET renderiza, POST procesa vía fetch/AJAX) |
| `/impacto/` | `impacto` | `impacto.html` | Material de auspicio, sin link en el menú a propósito |
| `/admin/` (o `DJANGO_ADMIN_URL`) | Django admin | — | Panel de administración |

La vista `contacto()` es la única con lógica real: valida los campos server-side (obligatorios, largo máximo igual al del modelo, email válido, `interes` dentro de las opciones), aplica rate limiting, guarda en base de datos, y manda un correo de aviso (best-effort: si el correo falla, el mensaje ya quedó guardado igual, solo se loguea la excepción).

## 1.6 Sistema visual

- **Paleta**: definida como custom properties CSS en `base.html` (`--c-navy`, `--c-navy-deep`, `--c-blue-soft`, `--c-green`, `--c-green-deep`, `--c-amber`, `--c-orange`, `--c-red`). Dos azules (uno para header/franjas, otro para el cuerpo) y un pie que degrada de navy a verde oscuro.
- **Tipografía**: Barlow Condensed (display, para todos los `h1`–`h6`, `.titulo-seccion`, cifras) + Helvetica Neue/Arial (cuerpo de texto). Auto-hospedada en `core/static/core/fonts/` — no se usa Google Fonts por CDN porque la CSP del sitio bloquea fuentes externas.
- **Cada vista trae su propio `<style>` inline** (protegido con `nonce="{{ request.csp_nonce }}"` por la CSP, ver 1.8) en vez de archivos CSS separados. Es una decisión deliberada del proyecto, no una migración pendiente.
- **Pelota 3D** (`pelota3d.js`): balón de vóleibol genérico generado por código (Three.js), no un modelo 3D importado. Genera tres mapas de textura (color, relieve, rugosidad) a partir de ruido procedural y una transformada de distancia sobre las costuras de los paneles. Ha pasado por varias iteraciones de ajuste de textura (ver Parte 2).
- **Menú móvil, header con sombra al hacer scroll, lightbox de la galería**: JS vanilla inline, sin ninguna librería de frontend.

## 1.7 Seguridad y hardening ya implementado

Todo esto **ya está hecho y commiteado**, no es parte de los pendientes:

- **`DEBUG`**: default `False` (seguro). Se activa con `DJANGO_DEBUG=True` en `.env` solo en desarrollo.
- **`SECRET_KEY`**: obligatoria si `DEBUG=False` — si falta, la app no arranca (`ImproperlyConfigured`) en vez de exponer secretos. En desarrollo cae a un valor conocido como inseguro por diseño.
- **HTTPS/HSTS**: `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (1 año, con subdominios y preload) — todo activo solo cuando `DEBUG=False`, para no romper `runserver` local sobre `http://`.
- **CSP estricta con nonces** (no la versión permisiva "report-only"): cada uno de los ~15 bloques `<style>`/`<script>` inline del sitio lleva `nonce="{{ request.csp_nonce }}"`, generado por request. Dominios externos permitidos explícitamente: `cdnjs.cloudflare.com` (three.js) y `www.instagram.com` (script + iframe + XHR del widget de posts embebidos).
- **Rate limiting**: `django-ratelimit`, 5 POST/minuto por IP en `/contacto/`, con caché en base de datos (`DatabaseCache`) para que el conteo se comparta entre los workers de Gunicorn en producción. Nota técnica: `django-ratelimit` marca `DatabaseCache` como "sin incremento atómico garantizado" (chequeo `E003`, silenciado a propósito) — decisión consciente: para el volumen de este sitio no se justifica sumar Redis/Memcached solo por esto.
- **URL del admin configurable** vía `DJANGO_ADMIN_URL` (default `admin/` si no se define).
- **Logging**: handler de consola siempre activo (para no quedar ciego con `DEBUG=False`). **Sentry opcional**: se activa solo si existe `SENTRY_DSN`.
- **Validación server-side completa** en el formulario de Contacto (antes solo confiaba en el `maxlength` del HTML).

`python manage.py check --deploy` ya se verificó limpio simulando variables de entorno de producción.

## 1.8 Testing y CI

- `core/tests.py`: 5 tests sobre `contacto()` — campo obligatorio faltante, email inválido, `interes` inválido, campo que excede el máximo de caracteres, y el caso exitoso (incluyendo que no falla aunque no haya `CONTACTO_DESTINATARIO` configurado).
- `.github/workflows/ci.yml`: en cada push/PR a `development` y `master`, instala dependencias, corre `manage.py test` y `manage.py check --deploy` (con variables de entorno de prueba).

## 1.9 Despliegue: mecanismo técnico

- **`Procfile`**:
  ```
  release: python manage.py migrate && python manage.py createcachetable
  web: gunicorn LMVEweb.wsgi:application --bind 0.0.0.0:$PORT
  ```
- **`build.sh`** (Build Command en Render, `bash build.sh`):
  ```bash
  pip install -r requirements.txt
  python manage.py collectstatic --noinput
  ```
  Importante: `collectstatic` va en el **build**, no en el `release` de Procfile — en Render, `release` corre en una instancia separada del contenedor final que sirve `web`, así que lo que ahí se escriba a disco no llega a producción. Esto ya se corrigió en el proyecto (commit `47151d2`), pero es un detalle no obvio si se edita el flujo de deploy más adelante.
- **Estáticos**: WhiteNoise con `CompressedManifestStaticFilesStorage` — cada archivo estático se sirve con un hash de su contenido en el nombre (ej. `logo-watermark.6235957d83a8.png`), lo que permite cachear "para siempre" en el navegador sin nunca servir contenido viejo tras un deploy, siempre que `collectstatic` corra en cada build.

## 1.10 Variables de entorno

Documentadas en `.env.example` (se commitea, sin valores reales):

| Variable | Obligatoria | Notas |
|---|---|---|
| `DJANGO_DEBUG` | No | `True` en local; en producción no se define (default `False`) |
| `DJANGO_SECRET_KEY` | Sí, si `DEBUG=False` | Generar con `get_random_secret_key()`; nunca commitear el valor real |
| `DJANGO_ALLOWED_HOSTS` | Sí, en producción | Dominios separados por coma |
| `DJANGO_ADMIN_URL` | No | Default `admin/` |
| `DATABASE_URL` | No | Sin definir, usa SQLite local; en Render la entrega el add-on de Postgres automáticamente |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | No | Gmail + contraseña de aplicación; sin esto, el correo del formulario solo se imprime en consola |
| `CONTACTO_DESTINATARIO` | No | A qué correo llega cada propuesta de auspicio |
| `SENTRY_DSN` | No | Sin esto, Sentry no se activa |

## 1.11 Correo saliente

SMTP de Gmail (cuenta con verificación en dos pasos + contraseña de aplicación), no un servicio transaccional dedicado (Resend/SendGrid). Elegido así porque, al no existir todavía el dominio propio, un remitente `@gmail.com` entrega con mejor reputación que un dominio nuevo sin DNS verificado. Se puede migrar a un proveedor dedicado más adelante sin tocar la lógica de la vista, solo las variables de entorno.

## 1.12 Control de versiones

- Repositorio en GitHub, cuenta personal (`maumontenegro99/LMVEweb`) — **pendiente migrar a una cuenta de organización de la Liga** (ver Parte 2).
- Dos ramas: `master` (estable / lo que se despliega) y `development` (trabajo activo). **`master` está ~20 commits atrás de `development`** — hay que sincronizarlas antes de conectar Render a una de las dos.
- El historial de git contiene un `db.sqlite3` viejo commiteado en una etapa muy temprana del proyecto (ya no está trackeado) y una `SECRET_KEY` de desarrollo marcada explícitamente como insegura. Ninguna es un secreto real de producción, pero si el repo llegó a ser público en algún momento, ambas cosas quedaron expuestas en el historial.

---

# PARTE 2 — Pendientes antes del deploy

## 2.1 Diseño y contenido (recién identificados)

1. **Embeds de Instagram descuadrados** — en Inicio (`home.html`), la fila de 3 posts embebidos (`.ig-card`, widget `instagram-media` + `embed.js`) se ve descuadrada en la parte inferior. El código ya tiene un comentario propio explicando por qué no se fuerza una altura fija (cada tarjeta crece a su alto natural para no cortar contenido) — hay que revisar si el descuadre es por eso o por otra causa.
2. **Logos del carrusel de colegios**: hoy hay 44 (`core/static/core/img/colegios/1.png` a `44.png`, referenciados en `home.html` por posición numérica). Faltan 2 por agregar y sobra 1 por sacar — falta definir cuáles exactamente.
3. **Vista Historia** (`proyecto.html`): actualizar fotos y descripciones. Hoy la línea de tiempo tiene tramos con datos concretos (de la Reseña Histórica 2026) y al menos un tramo (década de 2010) con texto genérico de continuidad marcado explícitamente como pendiente de material real (`.epoca-aviso`). Solo hay 2 fotos con fecha específica en el proyecto (`historia-1987.jpg`, `historia-1996.jpg`).
4. **Textura de la pelota 3D**: sigue sin convencer del todo. Historial de intentos en esta misma sesión:
   - Original: parecía hormigón (ruido submuestreado por debajo del límite de Nyquist en el mapa de relieve — causa raíz identificada y corregida).
   - Ajuste 1: se corrigió el muestreo, pero un ruido bien muestreado en el mapa de relieve da bollos regulares — pasó a parecer pelota de golf.
   - Ajuste 2: se quitó todo el grano del relieve (dejando solo costuras) y se agregó abullonado real de los paneles (domo suave por panel, calibrado con desenfoque para evitar artefactos de "origami"). El resultado no convenció — se sintió como plástico duro.
   - Estado actual: revertido al estado "golf" (commit `63c79b3`), que quedó como el mejor de los tres a criterio del product owner, aunque tampoco es el objetivo final. **Sigue abierto.**

## 2.2 Infraestructura y cuentas externas

En orden de dependencia (no todo bloquea el primer deploy):

**Bloqueante antes de tocar Render:**
- Sincronizar `master` con `development` (o decidir apuntar Render directo a `development` por ahora).
- Comprimir las ~69 fotos de la galería (17 MB hoy; se suben tal cual al hacer `collectstatic` en el build).
- Generar la contraseña de aplicación de Gmail real para `EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` (hoy en local el correo solo se imprime en consola).

**Los pasos de Render mismo:**
- Crear cuenta en Render y conectar el repo de GitHub.
- Crear la base PostgreSQL (plan Basic, ~USD 6/mes).
- Crear el Web Service: Build Command `bash build.sh`, Start Command del `Procfile`, plan Starter (~USD 7/mes).
- Cargar las variables de entorno (tabla completa en 1.10) — `DJANGO_SECRET_KEY` nueva, `DJANGO_ALLOWED_HOSTS` con el dominio de Render, `DATABASE_URL` (la entrega Render solo), credenciales de Gmail, `CONTACTO_DESTINATARIO`.
- Primer deploy (migraciones y `createcachetable` corren solos vía `release` del Procfile).
- Crear el superusuario de producción desde el Shell de Render (`python manage.py createsuperuser`) — es una base nueva, no hereda nada de local.
- Recorrer las 7 páginas en un navegador real contra la URL de Render, revisando la consola por errores de CSP (el test client de Django confirma que la cabecera se arma bien, pero no reemplaza un navegador de verdad).

**Dominio y Cloudflare (fase posterior, no bloquea salir en vivo primero en `*.onrender.com`):**
- Registrar `lmve.cl` en NIC Chile.
- Apuntar los nameservers a Render, esperar propagación DNS (24-48h).
- Cloudflare entra recién acá (no antes): protege/gestiona el DNS de un dominio que ya existe, no tiene nada que configurar hasta ese momento. Sirve además para activar correo gratis en `contacto@lmve.cl` (Cloudflare Email Routing, reenviando al Gmail real) sin necesidad de una casilla nueva de pago.

**No bloqueante, con dueño/decisión pendiente:**
- Cuenta de organización de GitHub para la Liga (para que el repo no dependa de la cuenta personal de Mauricio — ver `DEPLOY_PLAN_PARA_DIRIGENTES.md`, sección "¿De quién es el sitio?"). Mejor hacerlo temprano que a último momento.
- Favicon (no existe todavía).
- Vendorizar `three.js` localmente en vez de cargarlo desde `cdnjs.cloudflare.com` (saca una dependencia externa, no crítico).
- 2FA en `/admin/` (`django-otp`) — el admin hoy solo es alcanzable desde local, el riesgo real aparece cuando el sitio esté público.
- Cuenta de Sentry, si se quiere monitoreo de errores desde el día uno.

## 2.3 Orden sugerido

1. Resolver 2.1 (diseño/contenido) y la parte "bloqueante" de 2.2 en paralelo.
2. Mergear a `master`.
3. Crear cuenta Render + Postgres + Web Service + variables de entorno.
4. Primer deploy en `*.onrender.com`, QA manual, superusuario de producción.
5. Recién ahí: dominio + Cloudflare.
6. En cualquier momento, sin apuro: organización de GitHub, favicon, 2FA, Sentry.

---

# PARTE 3 — Resumen del proyecto

## 3.1 Para Mauricio (status técnico)

El proyecto pasó por dos etapas grandes en el trabajo reciente:

**Etapa 1 — Hardening pre-deploy (completa).** Se auditó el proyecto completo (arquitectura, configuración de producción, seguridad, manejo de secretos, calidad de código, optimización de consultas) y se implementó el checklist resultante de punta a punta: variables de entorno seguras, HTTPS/HSTS, CSP estricta con nonces, rate limiting, logging + Sentry opcional, validación server-side, tests, CI, `Procfile` + `build.sh` para Render. Todo esto está commiteado en `development` y verificado (`check --deploy` limpio, tests en verde).

En el camino aparecieron y se resolvieron dos incidentes reales, no cosméticos:
- Durante una reestructuración de ramas de git, un `git checkout master` sobrescribió silenciosamente el `db.sqlite3` local con una versión antigua del historial (de antes de que existiera el modelo `MensajePatrocinio`). Se recuperó el esquema con `migrate`, pero cualquier superusuario que hubiera existido antes de ese momento se perdió — hubo que crear uno nuevo.
- El `venv` local estaba armado con rutas de otra cuenta de Windows (`mauri` en vez de `Mauro`), roto desde el principio de esta sesión de trabajo. Se recreó desde cero.

**Etapa 2 — Diseño visual (en curso).** Tipografía de display (Barlow Condensed, auto-hospedada), rediseño del logo del header/pie (sin placa blanca, letras del wordmark blancas), reordenamiento del pie de página (Patrocinador + Nuestras Redes con iconos de línea propios en vez de logos de app genéricos), ajustes de contraste del logo de Molten, y varios intentos sobre la textura de la pelota 3D (todavía sin cerrar, ver 2.1).

**Lo que sigue** es la lista de la Parte 2: 4 pendientes de diseño/contenido recién identificados, más toda la parte operativa de conectar Render, generar credenciales reales, y eventualmente dominio + Cloudflare.

**Decisiones tomadas que vale la pena recordar** (para no revisitarlas sin motivo):
- Gmail SMTP en vez de Resend para el correo saliente, por ahora — se reevalúa cuando exista dominio propio verificado.
- `DatabaseCache` para el rate limiting en vez de Redis/Memcached — aceptado el trade-off de atomicidad no garantizada por el volumen de tráfico esperado.
- CSP estricta con nonces (no la versión permisiva "report-only" que proponía el plan original) — ya se relevaron y cubrieron los 3 dominios externos que el sitio realmente usa (`cdnjs.cloudflare.com`, `www.instagram.com`).

## 3.2 Para la Junta Directiva (avance del proyecto)

El sitio web de la Liga está en la recta final de la etapa de construcción, antes de publicarlo en internet.

**¿Qué se hizo?** Se terminó toda la parte de seguridad y "a prueba de fallos" del sitio: protección contra ataques comunes de internet, manejo seguro de las contraseñas técnicas, un sistema que evita que alguien inunde el formulario de contacto con mensajes falsos, y un mecanismo para enterarse si algo falla una vez que el sitio esté funcionando. Esta parte no se ve a simple vista navegando el sitio, pero es la que garantiza que sea seguro y estable cuando lo visite gente de verdad.

En paralelo, se avanzó en la parte visual: la tipografía de los títulos, el logo en el encabezado y el pie de página, y el ordenamiento de la información de contacto y del patrocinador en el pie.

**¿Qué falta?** Cuatro ajustes de contenido y diseño (arreglar cómo se ven los posts de Instagram embebidos, actualizar un par de logos de colegios, poner fotos y descripciones más completas en la sección Historia, y seguir puliendo el detalle visual de la pelota animada), y después los pasos administrativos para publicarlo: crear la cuenta en el servicio de hosting (Render), cargar las claves de acceso reales, y hacer una revisión final antes de anunciarlo. El registro del dominio `lmve.cl` y su conexión con Cloudflare quedan para una etapa posterior — el sitio puede salir en línea primero con una dirección temporal mientras eso se gestiona.

**¿Cuándo estaría listo?** Con los pendientes de diseño resueltos, la parte técnica para el primer despliegue está lista para ejecutarse en cuestión de días, no de semanas — ver el cronograma detallado en `DEPLOY_PLAN_PARA_DIRIGENTES.md`.
