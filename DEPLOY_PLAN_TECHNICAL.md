# Plan de Despliegue en Producción - LMVEweb
## Documento Técnico Profesional v1.0

---

## 1. Executive Summary

La plataforma LMVEweb es una aplicación Django 6.0.5 construida como un MVP interactivo para captura de patrocinadores. Se propone un despliegue en la plataforma PaaS Render con base de datos PostgreSQL gestionada, integrando Resend para transacciones de correo y NIC Chile para resolución de dominio .cl. La arquitectura garantiza alta disponibilidad, mitigación DDoS automática mediante Cloudflare, red privada (VPC) entre capas de aplicación y datos, y cumplimiento normativo chileno para protección de datos personales.

**Costo mensual estimado:** USD $13 + CLP $833 (amortización dominio anual)  
**Cronograma estimado:** 7-10 días continuos | ~40-60 horas  
**Complejidad técnica:** 6.5/10 para estudiante avanzado de Ingeniería Informática

---

## 2. Análisis de Arquitectura Actual y Transición

### 2.1 Estado Actual (Desarrollo Local)

```
Componente           | Tecnología      | Entorno
---------------------|-----------------|------------------
Framework web        | Django 6.0.5    | python manage.py runserver
Base de datos        | SQLite3         | Local (/db.sqlite3)
Archivos estáticos   | Servidos por DJ | Automático (DEBUG=True)
Servidor WSGI        | Django devserver| Síncrono, 1 worker
Forma de acceso      | localhost:8000  | Red local
Seguridad            | Mínima          | DEBUG=True, sin HTTPS
```

### 2.2 Arquitectura de Producción Propuesta

```
Internet (HTTPS)
    ↓
Cloudflare (Mitigación DDoS, WAF opcional)
    ↓
Render CDN Edge
    ↓
[Web Service: Gunicorn + Django + WhiteNoise]
    ↓ (Red privada VPC, sin egress billing)
[PostgreSQL Managed: Render Basic (256 MB)]
    ↓
Backups automáticos (+ pg_dump diario a S3/externo)
```

**Ventajas de esta arquitectura:**
- Servidor de aplicaciones siempre activo (Render Starter: $7/mes, 512 MB RAM)
- Base de datos sin expiración a 30 días (Render Basic: $6/mes)
- Tráfico interno entre app ↔ BD sin salida a internet (sin coste de egress)
- Certificados SSL/TLS automáticos (Let's Encrypt vía Render)
- DDoS bloqueado antes de llegar a la instancia web (Cloudflare)
- Escalabilidad vertical simple: incrementar RAM/CPU sin reconfiguración

---

## 3. Stack Tecnológico y Justificación de Componentes

### 3.1 Servidor de Aplicaciones: Gunicorn + WSGI

**Selección:** Gunicorn (worker model: pre-fork)

```bash
gunicorn --workers 4 --worker-class sync --bind 0.0.0.0:8000 \
  --timeout 60 --access-logfile - config.wsgi:application
```

**Justificación:**
- Benchmarks (2026) demuestran 2.44× más RPS que Uvicorn para cargas síncronas
- Django con ORM + base de datos relacional = sin necesidad de ASGI
- Pre-fork model reduce latencia p99 en aplicaciones CPU-bound moderadas
- Render soporta natively sin Docker overhead

**Alternativa descartada:** Uvicorn
- Necesitaría async/await en vistas (refactorización mayor)
- Peor rendimiento para aplicaciones síncronas
- Viable solo si hay WebSockets o streaming (no aplica)

### 3.2 Servicio de Archivos Estáticos: WhiteNoise

**Configuración:**

```python
# settings.py
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',  # PRIMER elemento
    'django.middleware.security.SecurityMiddleware',
    # ... resto de middleware
]

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

**Ventajas:**
- Evita S3/CloudFront (costo adicional)
- Compresión automática Gzip + Brotli
- Caché de larga duración (nombres de archivo hash)
- Inyecta SRI (Subresource Integrity) en templates si se configura

### 3.3 Base de Datos: PostgreSQL Managed (Render)

**Especificaciones:**
- Versión: PostgreSQL 15.x
- Almacenamiento: 500 MB incluidos (escalable)
- Backups automáticos: 7 días (sin configuración)
- Conexión: SSL/TLS obligatorio

**Migración desde SQLite:**

```bash
# 1. En entorno local, instalar dj_database_url
pip install dj_database_url

# 2. Actualizar settings.py para leer DATABASE_URL
import dj_database_url
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///db.sqlite3',
        conn_max_age=600
    )
}

# 3. Crear dump de SQLite y transformar a PostgreSQL
python manage.py dumpdata > data.json
# (Crear base de datos vacía en PostgreSQL)
python manage.py migrate  # Aplicar esquema
python manage.py loaddata data.json  # Restaurar datos
```

### 3.4 Correos Transaccionales: Resend

**Integración Django:**

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.resend.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'onboarding@resend.dev'  # Cambiar por API key en produción
EMAIL_HOST_PASSWORD = os.environ.get('RESEND_API_KEY')

# O usar SDK oficial
# pip install resend
from resend import Resend
client = Resend(api_key=os.environ.get('RESEND_API_KEY'))
```

**Plan utilizado:** Resend Free Tier
- 3.000 envíos/mes
- 100 envíos/día máximo
- Suficiente para MVP

**Escalamiento:** Plan Pro ($20/mes) si se excede

---

## 4. Plan de Implementación Detallado

### Fase 1: Refactorización de Entorno (Día 1)

**Objetivo:** Preparar el código para producción

**Tareas:**

1. **Migración SQLite → PostgreSQL local**
   ```bash
   pip install psycopg2-binary django-environ
   # Configurar PostgreSQL local
   createdb lmve_dev
   # Ejecutar migración (ver sección 3.3)
   ```

2. **Implementar gestión de secretos**
   ```
   # .env (no versionar en Git)
   DEBUG=False
   SECRET_KEY=django-insecure-...generado-aleatoriamente...
   DATABASE_URL=postgresql://user:pass@localhost/lmve_dev
   RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxx
   ALLOWED_HOSTS=localhost,127.0.0.1,lmve.cl,www.lmve.cl
   ```

   ```python
   # settings.py
   from pathlib import Path
   import os
   import dj_database_url
   from dotenv import load_dotenv
   
   load_dotenv()
   
   SECRET_KEY = os.getenv('SECRET_KEY')
   DEBUG = os.getenv('DEBUG', 'False') == 'True'
   ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')
   ```

3. **Auditar dependencias**
   ```bash
   pip install pip-audit safety
   pip-audit --fix
   safety check
   # Actualizar requirements.txt
   pip freeze > requirements.txt
   ```

### Fase 2: Configuración de Producción (Días 2-3)

**Objetivo:** Optimizar para Render

**Tareas:**

1. **Instalar y configurar Gunicorn**
   ```bash
   pip install gunicorn
   # requirements.txt debe incluir:
   gunicorn==21.2.0
   whitenoise==6.6.0
   python-dotenv==1.0.0
   psycopg2-binary==2.9.9
   django-environ==0.11.2
   dj-database-url==2.1.0
   ```

2. **Configurar WhiteNoise** (ver sección 3.2)
   ```bash
   python manage.py collectstatic --noinput
   # Verifica que `staticfiles/` contiene CSS, JS, imágenes comprimidas
   ```

3. **Crear Procfile para Render**
   ```
   # Procfile (raíz del proyecto)
   release: python manage.py migrate
   web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```

4. **Endurecimiento de seguridad en settings.py**
   ```python
   # HTTPS & Cookies
   SECURE_SSL_REDIRECT = True
   SESSION_COOKIE_SECURE = True
   CSRF_COOKIE_SECURE = True
   SECURE_HSTS_SECONDS = 31536000  # 1 año
   SECURE_HSTS_INCLUDE_SUBDOMAINS = True
   SECURE_HSTS_PRELOAD = True
   
   # Cabeceras de seguridad
   SECURE_CONTENT_TYPE_NOSNIFF = True
   SECURE_BROWSER_XSS_FILTER = True
   X_FRAME_OPTIONS = 'DENY'
   
   # CSP (Content Security Policy)
   CSP_DEFAULT_SRC = ("'self'",)
   CSP_SCRIPT_SRC = ("'self'", "www.instagram.com", "cdn.jsdelivr.net")
   CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")  # Optimizar sin unsafe-inline
   CSP_IMG_SRC = ("'self'", "data:", "https:")
   CSP_FONT_SRC = ("'self'", "data:")
   CSP_CONNECT_SRC = ("'self'", "www.instagram.com")
   ```

5. **Validación pre-deploy**
   ```bash
   python manage.py check --deploy
   # Debe retornar sin errores ni advertencias
   ```

### Fase 3: Despliegue en Render (Días 4-5)

**Objetivo:** Poner en línea la plataforma

**Tareas:**

1. **Crear cuenta en Render** (render.com)
   - Vincular repositorio GitHub
   - Autorizar acceso OAuth

2. **Crear Web Service**
   ```
   Configuración en Render Dashboard:
   - Name: lmve-web
   - Environment: Python 3.11
   - Build Command: pip install -r requirements.txt && python manage.py collectstatic --noinput
   - Start Command: gunicorn config.wsgi:application
   - Plan: Starter ($7/mes)
   - Auto-deploy: Enabled (rama main)
   ```

3. **Crear PostgreSQL Database**
   ```
   - Name: lmve-db
   - PostgreSQL Version: 15
   - Plan: Basic ($6/mes, 256 MB)
   ```

4. **Vincular Web Service a BD**
   ```
   Environment Variables en Web Service:
   - DATABASE_URL: (Copiar automáticamente de la BD)
   - DJANGO_SETTINGS_MODULE: config.settings
   - DJANGO_SECRET_KEY: (Generar aleatoriamente, NO usar dev)
   - ALLOWED_HOSTS: lmve.cl,www.lmve.cl,lmve-web.onrender.com
   - DEBUG: False
   - RESEND_API_KEY: re_xxxxxxxxxxxxxxxxxxxx
   ```

5. **Ejecutar migraciones en Render**
   - Ir a "Shell" en Render Dashboard
   - Ejecutar: `python manage.py migrate`
   - Crear superusuario: `python manage.py createsuperuser`

### Fase 4: Configuración de Dominio (Día 5-6)

**Objetivo:** Conectar dominio .cl a la plataforma

**Tareas:**

1. **Registrar dominio en NIC Chile** (https://www.nic.cl)
   - Costo: $9.990 CLP (anual)
   - Período: 1-10 años (descuentos progresivos)
   - Recomendación: 5 años ($49.950 CLP, ~20% descuento)

2. **Configurar DNS en Render**
   - Render proporciona nameservers o registros CNAME
   - Actualizar nameservers en NIC Chile:
     ```
     ns1.render.com
     ns2.render.com
     ns3.render.com
     ns4.render.com
     ```
   - TTL: 3600 segundos (1 hora)
   - Propagación: 24-48 horas

3. **Activar SSL en Render**
   - Render genera automáticamente certificado Let's Encrypt
   - Verificar en Dashboard: "Custom Domain → SSL"

4. **Verificación**
   ```bash
   # Esperar propagación DNS
   nslookup lmve.cl
   curl -I https://lmve.cl  # Debe retornar 200 con HTTPS
   ```

### Fase 5: Seguridad Avanzada y Monitoreo (Días 6-7)

**Objetivo:** Blindar la plataforma

**Tareas:**

1. **Rate Limiting en formulario de contacto**
   ```bash
   pip install django-ratelimit
   ```
   
   ```python
   # core/views.py
   from django_ratelimit.decorators import ratelimit
   
   @ratelimit(key='ip', rate='5/m', method='POST')
   def contacto(request):
       if request.method == 'POST':
           # ... lógica existente ...
   ```

2. **Protección del panel de admin**
   ```python
   # settings.py
   # Cambiar URL por defecto
   ADMIN_URL = 'secretadminurl/'  # Cambiar a algo único
   
   # Activar autenticación de dos factores
   pip install django-otp qrcode
   ```

3. **Implementar Sentry para monitoreo**
   ```bash
   pip install sentry-sdk
   ```
   
   ```python
   # settings.py
   import sentry_sdk
   from sentry_sdk.integrations.django import DjangoIntegration
   
   sentry_sdk.init(
       dsn=os.environ.get('SENTRY_DSN'),
       integrations=[DjangoIntegration()],
       traces_sample_rate=0.1,
       send_default_pii=False
   )
   ```

4. **Automatizar backups externos**
   ```bash
   # .github/workflows/backup-db.yml
   name: Daily Database Backup
   
   on:
     schedule:
       - cron: '0 2 * * *'  # 02:00 UTC diariamente
   
   jobs:
     backup:
       runs-on: ubuntu-latest
       steps:
         - name: Backup PostgreSQL
           env:
             DATABASE_URL: ${{ secrets.DATABASE_URL }}
           run: |
             pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
             # Subir a S3 o almacenamiento externo
   ```

5. **Auditoría de vulnerabilidades**
   ```bash
   # Integrar en CI/CD
   pip install bandit
   bandit -r core/ -f json > bandit-report.json
   ```

---

## 5. Configuración de Seguridad Específica

### 5.1 Base de Datos: Privilegios Mínimos

```sql
-- En PostgreSQL (Render)
CREATE ROLE lmve_app WITH LOGIN PASSWORD 'strong-random-password';
GRANT CONNECT ON DATABASE lmve TO lmve_app;
GRANT USAGE ON SCHEMA public TO lmve_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO lmve_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO lmve_app;

-- Usar esta credencial en DATABASE_URL (no la de admin)
```

### 5.2 CSP Estricto (Content Security Policy)

```python
# pip install django-csp
MIDDLEWARE = [
    'csp.middleware.CSPMiddleware',  # Temprano en la cadena
    # ...
]

CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "www.instagram.com")
CSP_STYLE_SRC = ("'self'",)  # Eliminar unsafe-inline cuando sea posible
CSP_IMG_SRC = ("'self'", "data:", "https:", "instagram.com")
CSP_CONNECT_SRC = ("'self'", "*.instagram.com")
CSP_FRAME_ANCESTORS = ("'none'",)
CSP_BASE_URI = ("'self'",)

# Modo report-only inicialmente
CSP_REPORT_ONLY = True
CSP_REPORT_URI = '/csp-report/'
```

### 5.3 Sanitización de Entrada

```bash
pip install bleach
```

```python
# core/utils.py
from bleach import clean, ALLOWED_TAGS, ALLOWED_ATTRIBUTES

ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u']
ALLOWED_ATTRIBUTES = {}

def sanitize_user_input(html_string):
    return clean(html_string, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
```

---

## 6. Checklist Técnico Previo a Go-Live

- [ ] `python manage.py check --deploy` sin advertencias
- [ ] `python manage.py collectstatic` ejecutado y verificado
- [ ] Base de datos migrada a PostgreSQL (no SQLite)
- [ ] `SECRET_KEY` rotada y diferente en producción
- [ ] DEBUG = False en settings de producción
- [ ] ALLOWED_HOSTS configurado correctamente
- [ ] HTTPS redirect habilitado (SECURE_SSL_REDIRECT = True)
- [ ] HSTS configurado (SECURE_HSTS_SECONDS >= 31536000)
- [ ] Cookies seguras (SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE)
- [ ] CSP implementado (en report-only o enforce)
- [ ] Rate limiting en formulario de contacto
- [ ] Panel admin en URL personalizada
- [ ] Resend API key configurada
- [ ] Sentry DSN configurada
- [ ] Backups automáticos configurados
- [ ] Dominio .cl registrado y DNS propagado
- [ ] SSL/TLS activado en Render
- [ ] Tests funcionales ejecutados en producción (humo básico)
- [ ] Logs centralizados monitoreados

---

## 7. Monitoreo Postdespliegue

**Métricas a vigilar:**

- Tasa de error 5xx (alertar si > 1%)
- Tiempo de respuesta p95 (referencia: < 500ms)
- Uso de BD (conexiones activas, queries lentas)
- Tasa de requests rechazados por rate limit
- Alertas de Sentry (excepciones no manejadas)

**Cadencia de revisión:** Diaria primera semana, luego semanal

---

## 8. Roadmap Post-MVP

**Semanas 1-2 (Estabilización):**
- Monitorear logs y errores
- Optimizar consultas lentas
- Ajustar rate limits si es necesario

**Mes 2:**
- Implementar analytics (Plausible, Fathom) si se requiere
- Opcionalmente: Cloudflare WAF para protección adicional

**Trimestre 2:**
- Considerar caché con Redis si tráfico crece
- Auditoría de seguridad profesional si presupuesto lo permite

---

**Documento preparado por:** Claude Code  
**Versión:** 1.0  
**Última actualización:** 2026-08-10  
**Vigencia:** Válido mientras Render y NIC Chile mantengan sus TOS actuales
