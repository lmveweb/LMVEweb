# Plan de Publicación del Sitio Web de la LMVE
## Una Guía Simple para Dirigentes

---

## ¿Qué vamos a hacer?

Imagina que tu sitio web de la Liga está ahora en una casa local (tu computadora), y solo tú puedes verlo. Lo que vamos a hacer es **mudar esa casa a un departamento en un edificio grande en Internet**, para que cualquiera pueda visitarlo desde cualquier parte del mundo, a cualquier hora, sin necesidad de tu computadora encendida.

**En términos simples:**
- Hoy: El sitio está en `localhost:8000` (solo en tu computadora)
- Después: El sitio estará en `https://lmve.cl` (en Internet, siempre disponible)

---

## ¿Cuánto va a costar?

**En pesos chilenos, mes a mes:**

| Concepto | Costo mensual aproximado | Qué es |
|----------|--------------------------|--------|
| **Servidor web** (donde vive el sitio) | ~$6.500 CLP | Lo mantiene encendido 24/7 |
| **Base de datos** (donde se guardan los contactos) | ~$5.500 CLP | Guarda los mensajes de patrocinio |
| **Dominio .cl** (lmve.cl) | ~$830 CLP* | *Se paga una vez al año ($9.990 CLP); acá dividido en 12 solo para comparar |
| **Envío de correos** (aviso de contactos) | Gratis** | Hasta 3.000 envíos al mes |
| **Certificado de seguridad (HTTPS)** | Gratis | Automático |
| **Protección contra ataques** | Gratis | Automático |
| | | |
| **TOTAL** | **~$12.800 CLP al mes** | ~$154.000 CLP al año |

Como referencia, es menos de lo que cuesta un plan de streaming — y cubre tener el sitio siempre disponible, protegido y con backups automáticos.

**\*El dominio no se cobra mes a mes**, es un pago único de $9.990 CLP una vez al año; se muestra dividido en 12 solo para que el total mensual sea comparable con el resto.

**\*\*El correo es gratis hasta 3.000 envíos al mes.** Si llegan más de 100 propuestas de auspicio por día (poco probable), pasamos a un plan pago de ~$18.000 CLP/mes.

---

## ¿Dónde va a vivir el sitio? (Render)

Hemos elegido una empresa llamada **Render** que es como una inmobiliaria tecnológica. Render:

✅ Mantiene tu sitio encendido 24/7  
✅ Te protege automáticamente de ataques en Internet  
✅ Hace backups (copias de seguridad) sin que hagas nada  
✅ Renueva los certificados de seguridad automáticamente  
✅ Es confiable y usada por empresas grandes

**Alternativas que descartamos:**
- Netlify / Vercel: Orientadas a otro tipo de sitios (no Django)
- Heroku: Más caro, ya no tiene plan gratuito
- Railway: Más caro que Render, facturas impredecibles

---

## ¿Cuánto tiempo va a tomar?

**Cronograma estimado: 1-2 semanas**

| Fase | Descripción | Duración | Qué pasa |
|------|-------------|----------|----------|
| **Semana 1, Día 1** | Preparar el código | 1 día | Convertimos SQLite (base de datos local) a PostgreSQL (base de datos de Internet) |
| **Semana 1, Días 2-3** | Configurar seguridad | 2 días | Activamos cerraduras digitales, certificados, protecciones |
| **Semana 1, Días 4-5** | Subir a Render | 2 días | El sitio se traslada a Internet; primeras pruebas |
| **Semana 1, Días 6-7** | Conectar dominio | 1-2 días | Vinculamos lmve.cl al servidor; esperar que la web sepa dónde buscar |
| **Semana 2** | Vigilancia y ajustes | ~3 días | Verificamos que todo funcione; arreglamos cosas pequeñas |

**¿Qué significa "esperar que la web sepa dónde buscar"?**  
Internet tiene un "listín telefónico global" que dice "lmve.cl está en esta dirección IP". Cuando cambias ese registro, tarda entre 24 y 48 horas en propagarse a todos los rincones del mundo. No hay nada que hacer durante ese tiempo, solo esperar.

---

## ¿Qué riesgos hay y cómo los evitamos?

### Riesgo 1: Ataques en Internet (DDoS)

**¿Qué es?** Alguien envía millones de visitantes falsos para que el sitio se caiga.

**Cómo lo evitamos:**
- Render está detrás de Cloudflare (una red global que filtra ataques)
- Cloudflare bloquea tráfico malicioso antes de que llegue a tu servidor
- Costo: $0 (incluido en Render)

### Riesgo 2: Datos personales robados

**¿Qué es?** Alguien intercepta los correos o datos de contactos de patrocinadores.

**Cómo lo evitamos:**
- Usamos HTTPS (conexión cifrada, como en tu banco)
- Guardamos las contraseñas de forma segura (no en texto plano)
- Base de datos solo acepta conexiones desde el servidor web (no desde Internet directamente)
- Hacer backups diarios en un lugar seguro (si algo sale mal, recuperamos los datos)

### Riesgo 3: Hacker accede al panel de admin

**¿Qué es?** Alguien adivina la contraseña del administrador del sitio.

**Cómo lo evitamos:**
- Cambiar la dirección del panel de admin (/admin) por algo secreto
- Usar contraseñas fuertes
- Opcionalmente: Activar autenticación de dos factores (tener que confirmar con el teléfono)

### Riesgo 4: Factura sorpresa por ataque (como le pasó a alguien en Netlify)

**¿Qué es?** Un ataque consume mucho ancho de banda y te llega una factura de miles de dólares.

**Cómo lo evitamos:**
- Render tiene precios fijos (no hay sorpresas)
- Puedes establecer un límite máximo de gasto
- Cloudflare absorbe la mayoría de los ataques sin costo adicional

---

## Cumplimiento de Leyes en Chile

Tu sitio tiene un **formulario de contacto** donde los patrocinadores envían su nombre, correo y mensaje. Por ley chilena, eso significa que debes:

✅ **Avisar que recopilas datos** (Política de Privacidad)  
✅ **Decir para qué los usas** (Solo para contacto / auspicio)  
✅ **Prometer que los proteges** (Cifrado, backups, acceso restringido)  
✅ **Permitir que causen de baja, corrijan o eliminen sus datos** (Si alguien quiere que bores su correo, puedes hacerlo)  
✅ **Avisar si hay Instagram embebido** (Porque Instagram también recopila datos)  

**Penas por no cumplir:** Multas de hasta $1.300 millones de pesos.

**Solución:** Agregaremos una Política de Privacidad simple y un aviso en el formulario. Nada complicado, solo transparencia.

---

## Pasos Principales (Lo que Necesitamos Hacer)

### Paso 1: Registrar dominio
**Dónde:** NIC Chile (https://www.nic.cl)  
**Costo:** $9.990 CLP / año  
**Tiempo:** 15 minutos  
**Quién:** Mauricio o alguien autorizado de la Liga  

### Paso 2: Crear cuenta en Render
**Dónde:** render.com  
**Costo:** Gratis (pagas después si usas servicios)  
**Tiempo:** 10 minutos  
**Quién:** El estudiante de Ingeniería Informática  

### Paso 3: Subir el código
**Qué:** Conectar GitHub a Render (solo un clic)  
**Tiempo:** 5 minutos de configuración + 5-10 minutos de compilación  
**Quién:** El estudiante  

### Paso 4: Conectar dominio .cl
**Qué:** Decirle a NIC Chile "lmve.cl ahora está en Render"  
**Tiempo:** 5 minutos de configuración + 24-48 horas de propagación  
**Quién:** El estudiante (Mauricio autoriza)  

### Paso 5: Vigilar que todo funcione
**Qué:** Revisar logs, probar formulario, confirmar HTTPS  
**Tiempo:** 30 minutos diarios primera semana, después mensual  
**Quién:** El estudiante + alguien de la Liga para validar desde el navegador  

---

## ¿De quién es el sitio? (Cuenta de Organización, no Personal)

Mauricio ofreció acompañar el sitio durante **6 meses** después de publicarlo. Pasado ese tiempo, la Liga tiene que poder seguir operándolo sola, sin depender de él.

**El problema, si no lo planificamos:** hoy, tanto el código (GitHub) como el servidor (Render) y el dominio se crearían a nombre personal de Mauricio. Es como si el título de propiedad del departamento quedara a su nombre en vez de al nombre del Club — el día que Mauricio ya no esté disponible, "traspasar" todo de golpe es engorroso y riesgoso (contraseñas, cuentas, dominios).

**El plan:** crear una **cuenta de organización** (a nombre de la Liga, no de una persona) desde el principio, en los tres lugares donde vive el proyecto:

| Servicio | Hoy (a evitar) | Plan (cuenta de organización) |
|---|---|---|
| **GitHub** (donde vive el código) | Cuenta personal de Mauricio | Organización de GitHub a nombre de la LMVE — gratis, ilimitada |
| **Render** (donde vive el servidor) | Cuenta personal | Cuenta/equipo creado con un correo institucional de la Liga |
| **Dominio lmve.cl** | A nombre personal | Registrado con los datos de la Liga (no el RUT personal de Mauricio) |

Con esto, Mauricio queda como **colaborador temporal** durante los 6 meses de soporte — no como dueño. Al terminar ese período, simplemente se le quita el acceso: no hay nada que "traspasar" de urgencia, porque la propiedad siempre fue de la Liga.

**Qué necesitamos de la Junta Directiva para esto:**
- Un correo institucional de la Liga (para crear las cuentas de GitHub y Render)
- Confirmar quién de la Junta va a quedar como segundo administrador (además de Mauricio, mientras dure el soporte), para que no dependa de una sola persona ni siquiera durante esos 6 meses

---

## Antes y Después

### HOY (Antes)

```
Visitante quiere ver lmve.cl
        ↓
Busca en Google
        ↓
Encuentra sitio viejo (hacked, fuera de línea, o sin sitio web)
        ↓
Se va a otro lado 😞
```

### DESPUÉS (Pasado mañana)

```
Visitante quiere ver lmve.cl
        ↓
Digita lmve.cl en navegador
        ↓
Llega a sitio moderno, seguro, siempre disponible
        ↓
Lee sobre la Liga, ve fotos de los equipos
        ↓
Completa formulario de contacto (protegido)
        ↓
¡Hablamos con el patrocinador! 🎉
```

---

## Preguntas Frecuentes

### ¿Qué pasa si se cae el servidor?
Render lo reinicia automáticamente. Si algo anda mal, Sentry (un monitor) te avisa al teléfono.

### ¿Puedo cambiar el sitio después de subirlo?
Sí. El estudiante hace cambios en GitHub, Render los compila automáticamente. Tarda 5-10 minutos.

### ¿Qué pasa si alguien piratiza el sitio?
Render guarda versiones antiguas (puedes rollback en 1 click). Además, hay logs de quién accedió y cuándo.

### ¿Si paso a otra plataforma después, pierdo los datos?
No. Hacer un backup (copia de seguridad) de la base de datos toma 5 minutos. Puedes llevar esos datos a cualquier lado.

### ¿Necesito cambiar contraseñas después de subir?
Sí, una sola vez. La SECRET_KEY (contraseña maestra de Django) debe ser única en producción.

### ¿Cuántos visitantes puede soportar el servidor?
Con el plan Starter ($7/mes), unos **500-1.000 visitantes simultáneos** sin problema. La Liga no alcanza eso nunca. Si crece, escalamos a más RAM ($10-15/mes extra).

### ¿Se me van a perder los correos de patrocinadores?
No. Cada correo se guarda en la base de datos. Si NIC Chile, Render o Resend cierran (muy improbable), podemos exportar todos los datos en 5 minutos.

---

## Cronograma Real (Con Márgenes)

```
SEMANA 1
Lunes    ▓▓▓ Preparar código (1 día)
Martes   ▓▓▓▓▓▓ Seguridad (2 días)
Miércoles-Viernes ▓▓▓▓▓▓▓▓ Subir a Render (2.5 días)

SEMANA 2
Lunes-Martes ▓▓▓ Conectar dominio + espera DNS (2 días)
Miércoles-Viernes ▓▓▓▓ Vigilancia y ajustes (2 días)

SEMANA 3 (Margen de error)
Lunes-Martes ▓▓ Resolver imprevistos si los hay

TOTAL: 8-10 días hábiles (2 semanas calendario)
```

---

## Checklist Para Dirigentes (Antes de Dar el Visto Bueno)

- [ ] Entiendo que el sitio va a estar siempre en línea (24/7)
- [ ] Entiendo que cuesta ~$13 USD + $9.990 CLP al año
- [ ] Entiendo que debo publicar una Política de Privacidad
- [ ] Autorizamos a Mauricio a registrar el dominio lmve.cl **a nombre de la Liga**
- [ ] Autorizamos al estudiante a crear cuenta en Render, **como cuenta de organización, no personal**
- [ ] Vamos a crear una Organización de GitHub para la Liga (no dejar el código en una cuenta personal)
- [ ] Designamos a un segundo dirigente como administrador, además de Mauricio, durante los 6 meses de soporte
- [ ] Confirmo que todos los datos de contactos se guardarán en PostgreSQL (más seguro que SQLite)
- [ ] Entiendo que si hay ataque, Cloudflare nos protege automáticamente
- [ ] Estamos preparados para revisar logs si algo sale mal

---

## Después de Ir en Vivo: Tareas Mensuales

**Primeravezes (Semana 1-2):**
- Revisar sitio desde diferentes navegadores
- Probar formulario de contacto (mandar correos de prueba)
- Confirmar que emails llegan correctamente
- Verificar que todas las imágenes, videos, logos cargan

**Mensualmente:**
- Revisar estadísticas de visitantes (si es que activamos Analytics)
- Revisar si hay alertas de seguridad
- Hacer backup manual de base de datos (como copia de seguridad extra)

**Anualmente:**
- Renovar dominio .cl (antes de que expire)
- Revisar seguridad con especialista (recomendable, presupuesto separado)

---

## En Caso de Emergencia

**¿Se cae el sitio?**  
→ Render lo reinicia automático (5 minutos máximo)

**¿Pierde datos alguien en el formulario?**  
→ Está guardado en base de datos en Render (verificar logs)

**¿Entra alguien no autorizado?**  
→ Cambiar contraseñas inmediatamente, revisar logs

**¿Dominio deja de funcionar?**  
→ Verificar que NIC Chile no lo haya suspendido por falta de pago; renovar si es necesario

**¿Cae la base de datos?**  
→ Render hace backups diarios automáticos; recuperar en 1 click

---

## Conclusión

En dos semanas, la LMVE tendrá un sitio web profesional, seguro y siempre disponible. El costo es mínimo (~$15 USD/mes), y la inversión inicial (tiempo del estudiante) es educativa para él también.

**¿Listo para ir en vivo?** 🚀

---

**Documento preparado para:** Junta Directiva - LMVE  
**Simplificado por:** Claude Code  
**Fecha:** Agosto 2026  
**Validez:** 1 año (2026-2027)
