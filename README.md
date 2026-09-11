<div align="center">
  <img src="core/static/core/img/logo-full.png" alt="LMVE" width="220"><br><br>

  # LMVEweb

  Sitio web oficial de la **Liga Metropolitana de Voleibol Escolar** — historia, multimedia y captación de auspicios.

  [![CI](https://github.com/lmveweb/LMVEweb/actions/workflows/ci.yml/badge.svg?branch=development)](https://github.com/lmveweb/LMVEweb/actions/workflows/ci.yml)
  ![Django](https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white)
  ![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
  [![Estado](https://img.shields.io/badge/estado-en_producción-2E7D32)](https://ligamve.cl)
</div>

---

## 📋 Sobre el proyecto

Sitio institucional de la LMVE, fundada en 1987, en producción en **[ligamve.cl](https://ligamve.cl)**. Siete vistas públicas: Inicio, Historia, Sobre la LMVE, Equipo, Multimedia, Contacto y Política de Privacidad.

El formulario de Contacto guarda cada propuesta de patrocinio en base de datos **y** avisa por correo, con rate limiting, honeypot, chequeo de tiempo de envío y (opcional) Cloudflare Turnstile para frenar spam.

| Vista | Ruta | Descripción |
|---|---|---|
| Inicio | `/` | Hero, cifras, redes sociales, colegios participantes |
| Historia | `/historia/` | Línea de tiempo por épocas, desde 1987 |
| Sobre la LMVE | `/sobre/` | Visión y misión |
| Equipo | `/equipo/` | Directiva, coordinadores y staff |
| Multimedia | `/multimedia/` | Galería de fotos con lightbox |
| Contacto | `/contacto/` | Formulario de auspicio → guarda en BD + envía correo |
| Política de Privacidad | `/privacidad/` | Política de privacidad y uso de datos |

---

## 🛠️ Stack técnico

- **Backend:** Django 6.0.5
- **Estáticos:** WhiteNoise (con hash de contenido para cache-busting)
- **Base de datos:** SQLite en desarrollo · PostgreSQL en producción
- **Seguridad:** Content-Security-Policy con nonces, HSTS, rate limiting (`django-ratelimit`)
- **Anti-spam en Contacto:** honeypot + chequeo de tiempo de envío (siempre activos) + Cloudflare Turnstile (opcional, activa solo con `TURNSTILE_SECRET_KEY`)
- **SEO técnico:** `robots.txt` + `sitemap.xml` (`django.contrib.sitemaps`), meta description/canonical/Open Graph por vista, JSON-LD (`WebSite` + `SportsOrganization`) en Inicio
- **Correo:** SMTP (Gmail + contraseña de aplicación), con fallback a consola en local
- **Monitoreo:** Sentry (opcional, activa solo con `SENTRY_DSN`)
- **Despliegue objetivo:** Render + PostgreSQL administrado

---

## 🚀 Cómo correrlo en local

```bash
git clone https://github.com/lmveweb/LMVEweb.git
cd LMVEweb

python -m venv venv
venv\Scripts\Activate.ps1        # Windows (PowerShell)
# source venv/bin/activate       # macOS / Linux

pip install -r requirements.txt

copy .env.example .env           # Windows
# cp .env.example .env           # macOS / Linux

python manage.py migrate
python manage.py createcachetable   # tabla de cache para el rate limiting
python manage.py runserver
```

Abrir **http://127.0.0.1:8000/**. Con el `.env` recién copiado (`DJANGO_DEBUG=True`), no hace falta configurar nada más para desarrollar — el correo del formulario de Contacto se imprime en la terminal en vez de enviarse de verdad.

### Correr los tests

```bash
python manage.py test
```

<details>
<summary><strong>Variables de entorno</strong> (ver <code>.env.example</code> para la lista completa)</summary>

| Variable | Para qué sirve | Obligatoria |
|---|---|---|
| `DJANGO_DEBUG` | `True` en local, `False` (o vacío) en producción | No — default `False` |
| `DJANGO_SECRET_KEY` | Clave de firma de Django | Sí, si `DJANGO_DEBUG=False` |
| `DJANGO_ALLOWED_HOSTS` | Dominios permitidos, separados por coma | Sí, en producción |
| `DJANGO_ADMIN_URL` | Ruta del panel de admin (default `admin/`) | No |
| `SITE_URL` | Origen canónico para sitemap, robots.txt y meta de SEO | No — default `http://127.0.0.1:8000` |
| `DATABASE_URL` | Postgres en producción; sin definir usa SQLite local | No |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | Gmail + contraseña de aplicación | No — sin esto, el correo solo se imprime en consola |
| `CONTACTO_DESTINATARIO` | A qué correo llega cada propuesta de auspicio | No |
| `SENTRY_DSN` | Activa el monitoreo de errores | No |
| `TURNSTILE_SITE_KEY` / `TURNSTILE_SECRET_KEY` | Verificación anti-spam (Cloudflare Turnstile) en Contacto | No — sin esto, esa capa no corre (quedan igual el honeypot y el chequeo de tiempo) |

</details>

---

## 📦 Despliegue

En producción en **Render** (`ligamve.cl`), con PostgreSQL administrado y DNS/proxy en Cloudflare. El build corre `build.sh` (instala dependencias + `collectstatic`); el `Procfile` aplica migraciones y levanta Gunicorn. Cada push a `master` dispara un redeploy automático.

---

## 🌱 Ramas

- **`master`** — versión estable / lo que está (o va a estar) en producción
- **`development`** — trabajo activo; se mergea a `master` cuando algo está listo

---

## 🤝 Organización del proyecto

El repositorio vive en una **cuenta de organización de la LMVE** (`github.com/lmveweb`), no en una cuenta personal — así el proyecto no depende de una sola persona una vez terminado el período de soporte.

<div align="center">
  <sub>Liga Metropolitana de Voleibol Escolar · Fundada en 1987 · "Educar a Través del Deporte"</sub>
</div>
