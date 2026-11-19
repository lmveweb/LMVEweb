/* Formulario de Noticias en el panel de administración.

   1. Pestañas: Texto, Vista previa, Fotos y Editar portada, para no
      tener que bajar por un formulario larguísimo. Sin JavaScript se ve
      todo seguido (y la vista previa no aparece: la arma este script).
   2. Editor de la foto de portada: recortar, girar, voltear y ajustar
      brillo, contraste y color, con vista previa de cómo queda arriba de
      la noticia, en su tarjeta y al compartir el link. El editor solo
      anota los ajustes en un campo oculto (portada_ajustes); la foto la
      edita el servidor al guardar, con las mismas fórmulas
      (core/imagenes.py, aplicar_ajustes).

   En un archivo y no en el HTML: la política de seguridad del sitio
   (CSP) no deja correr scripts escritos dentro de la página. Por lo
   mismo, los tamaños y posiciones se asignan con element.style (eso la
   CSP sí lo permite) y no con atributos style="". */
(function () {
    'use strict';

    /* =================================================================
       PESTAÑAS
       ================================================================= */
    var PESTANAS = [
        { id: 'texto', nombre: 'Texto', piezas: ['fieldset.pestana-texto'] },
        { id: 'vista', nombre: 'Vista previa', piezas: ['fieldset.pestana-vista'] },
        { id: 'fotos', nombre: 'Fotos', piezas: ['fieldset.pestana-fotos', '#fotos-group'] },
        { id: 'editor', nombre: 'Editar portada', piezas: ['fieldset.pestana-editor'] }
    ];

    function guardarPestana(id) {
        try { sessionStorage.setItem('noticia-pestana:' + location.pathname, id); } catch (e) { /* sin almacenamiento */ }
    }
    function pestanaGuardada() {
        try { return sessionStorage.getItem('noticia-pestana:' + location.pathname); } catch (e) { return null; }
    }

    function armarPestanas() {
        var primera = document.querySelector('fieldset.pestana');
        if (!primera) return;

        var barra = document.createElement('div');
        barra.className = 'pestanas-noticia';
        barra.setAttribute('role', 'tablist');
        barra.setAttribute('aria-label', 'Partes de la noticia');
        primera.parentNode.insertBefore(barra, primera);

        var botones = {};
        var paneles = {};
        var conError = null;

        PESTANAS.forEach(function (pestana) {
            var panel = document.createElement('div');
            panel.className = 'pestana-panel';
            panel.id = 'pestana-' + pestana.id;
            panel.setAttribute('role', 'tabpanel');
            pestana.piezas.forEach(function (selector) {
                var pieza = document.querySelector(selector);
                if (pieza) panel.appendChild(pieza);
            });
            paneles[pestana.id] = panel;

            var boton = document.createElement('button');
            boton.type = 'button';
            boton.className = 'pestana-boton';
            boton.id = 'boton-' + pestana.id;
            boton.setAttribute('role', 'tab');
            boton.setAttribute('aria-controls', panel.id);
            boton.textContent = pestana.nombre;
            if (panel.querySelector('.errorlist, .errornote, .errors')) {
                boton.classList.add('pestana-boton--error');
                boton.textContent = pestana.nombre + ' (revisar)';
                if (!conError) conError = pestana.id;
            }
            boton.addEventListener('click', function () { mostrar(pestana.id, true); });
            barra.appendChild(boton);
            botones[pestana.id] = boton;
        });

        // Los paneles van seguidos, justo después de la barra, en el
        // orden de PESTANAS; "Publicación" queda después de todos, junto
        // a los botones de guardar.
        var ancla = barra;
        PESTANAS.forEach(function (pestana) {
            ancla.parentNode.insertBefore(paneles[pestana.id], ancla.nextSibling);
            ancla = paneles[pestana.id];
        });
        var publicacion = document.querySelector('fieldset.pestana-publicacion');
        if (publicacion) ancla.parentNode.insertBefore(publicacion, ancla.nextSibling);

        function mostrar(id, recordar) {
            PESTANAS.forEach(function (pestana) {
                var activa = pestana.id === id;
                paneles[pestana.id].hidden = !activa;
                botones[pestana.id].setAttribute('aria-selected', activa ? 'true' : 'false');
                botones[pestana.id].classList.toggle('pestana-boton--activa', activa);
            });
            if (recordar) guardarPestana(id);
            if (id === 'editor') editor.mostrar();
            if (id === 'vista') vistaPrevia.actualizar();
        }

        // Al volver con errores se abre la pestaña que hay que corregir;
        // si no, la última que se usó.
        var guardada = pestanaGuardada();
        var valida = PESTANAS.some(function (p) { return p.id === guardada; });
        mostrar(conError || (valida ? guardada : 'texto'), false);

        // Flechas izquierda/derecha para moverse entre pestañas con el teclado.
        barra.addEventListener('keydown', function (evento) {
            if (evento.key !== 'ArrowRight' && evento.key !== 'ArrowLeft') return;
            var ids = PESTANAS.map(function (p) { return p.id; });
            var actual = ids.indexOf(document.activeElement.id.replace('boton-', ''));
            if (actual < 0) return;
            var siguiente = (actual + (evento.key === 'ArrowRight' ? 1 : ids.length - 1)) % ids.length;
            mostrar(ids[siguiente], true);
            botones[ids[siguiente]].focus();
            evento.preventDefault();
        });

        // Botón para ir directo al editor desde la pestaña Fotos.
        document.addEventListener('click', function (evento) {
            var enlace = evento.target.closest('[data-ir-a-pestana]');
            if (!enlace) return;
            evento.preventDefault();
            mostrar(enlace.getAttribute('data-ir-a-pestana'), true);
            window.scrollTo(0, barra.getBoundingClientRect().top + window.scrollY - 10);
        });
    }

    /* =================================================================
       VISTA PREVIA

       Manda lo escrito en el formulario (sin guardarlo) a la vista previa
       del servidor, que responde con la página de la noticia; la
       respuesta se abre en el recuadro de la pestaña. Se manda con un
       formulario aparte, creado acá, porque el del panel no puede tener
       otro adentro.
       ================================================================= */
    var vistaPrevia = {
        actualizar: function () {
            var raiz = document.querySelector('[data-vista-previa]');
            var principal = document.getElementById('noticia_form');
            if (!raiz || !principal) return;

            var envio = document.getElementById('envio-vista-previa');
            if (!envio) {
                envio = document.createElement('form');
                envio.id = 'envio-vista-previa';
                envio.method = 'post';
                envio.action = raiz.getAttribute('data-url');
                envio.target = 'marco-vista-previa';
                envio.hidden = true;
                document.body.appendChild(envio);
            }
            envio.textContent = '';

            function campo(nombre, valor) {
                var input = document.createElement('input');
                input.type = 'hidden';
                input.name = nombre;
                input.value = valor;
                envio.appendChild(input);
            }
            function valor(nombre) {
                var el = principal.querySelector('[name="' + nombre + '"]');
                return el ? el.value : '';
            }
            campo('csrfmiddlewaretoken', valor('csrfmiddlewaretoken'));
            ['titulo', 'fecha', 'autor', 'resumen', 'cuerpo'].forEach(function (nombre) {
                campo(nombre, valor(nombre));
            });
            campo('noticia', raiz.getAttribute('data-noticia') || '');
            var hayFotosNuevas = Array.prototype.some.call(
                principal.querySelectorAll('input[type="file"]'),
                function (input) { return input.files && input.files.length > 0; }
            );
            campo('fotos_sin_guardar', hayFotosNuevas ? '1' : '0');

            raiz.classList.add('vista-previa--cargando');
            envio.submit();
        }
    };

    function iniciarVistaPrevia() {
        var raiz = document.querySelector('[data-vista-previa]');
        if (!raiz) return;
        var marco = raiz.querySelector('iframe');
        marco.addEventListener('load', function () { raiz.classList.remove('vista-previa--cargando'); });
        raiz.addEventListener('click', function (evento) {
            var boton = evento.target.closest('button');
            if (!boton) return;
            if (boton.hasAttribute('data-actualizar')) {
                vistaPrevia.actualizar();
            } else if (boton.hasAttribute('data-ancho')) {
                raiz.setAttribute('data-dispositivo', boton.getAttribute('data-ancho'));
                Array.prototype.forEach.call(raiz.querySelectorAll('[data-ancho]'), function (b) {
                    b.setAttribute('aria-pressed', b === boton ? 'true' : 'false');
                });
            }
        });
    }

    /* =================================================================
       EDITOR DE LA PORTADA
       ================================================================= */
    var POR_DEFECTO = {
        rotacion: 0, voltear: false, x: 0, y: 0, ancho: 1, alto: 1,
        brillo: 1, contraste: 1, saturacion: 1
    };
    var MINIMO = 0.05;          // recorte mínimo: 5 % del ancho o del alto
    var LADO_MAXIMO = 1400;     // la foto base del editor, en px (rapidez)

    var editor = {
        listo: false,
        estado: null,
        proporcion: null,       // ancho/alto del recorte en px, o null (libre)
        imagen: null,           // la foto tal como se subió
        base: null,             // canvas con la foto girada y volteada
        mostrar: function () {}
    };

    function copia(obj) { return JSON.parse(JSON.stringify(obj)); }
    function limitar(v, min, max) { return Math.min(Math.max(v, min), max); }

    function iniciarEditor() {
        var raiz = document.getElementById('editorPortada');
        var campo = document.getElementById('id_portada_ajustes');
        if (!raiz || !campo) return;

        var cuerpo = document.getElementById('editorCuerpo');
        var vacio = document.getElementById('editorVacio');
        var sinJs = document.getElementById('editorSinJs');
        var lienzo = document.getElementById('editorLienzo');
        var canvas = document.getElementById('editorCanvas');
        var recorte = document.getElementById('editorRecorte');
        var archivo = document.getElementById('id_portada_archivo');
        var titulo = document.getElementById('id_titulo');
        if (sinJs) sinJs.hidden = true;

        // Ajustes guardados (al editar una noticia que ya tiene portada).
        var estado = copia(POR_DEFECTO);
        try {
            var leidos = JSON.parse(campo.value || '{}');
            Object.keys(POR_DEFECTO).forEach(function (clave) {
                if (clave in leidos) estado[clave] = leidos[clave];
            });
        } catch (e) { /* ajustes ilegibles: se parte de cero */ }
        editor.estado = estado;

        function anotar() {
            var redondeado = {};
            Object.keys(estado).forEach(function (clave) {
                var v = estado[clave];
                redondeado[clave] = typeof v === 'number' ? Math.round(v * 10000) / 10000 : v;
            });
            campo.value = JSON.stringify(redondeado);
        }

        function filtro() {
            return 'brightness(' + estado.brillo + ') contrast(' + estado.contraste + ') saturate(' + estado.saturacion + ')';
        }

        /* --- Foto base: la original girada y volteada ------------------ */
        function construirBase() {
            var img = editor.imagen;
            var escala = Math.min(1, LADO_MAXIMO / Math.max(img.naturalWidth, img.naturalHeight));
            var w = Math.round(img.naturalWidth * escala);
            var h = Math.round(img.naturalHeight * escala);
            var girada = estado.rotacion === 90 || estado.rotacion === 270;
            var base = document.createElement('canvas');
            base.width = girada ? h : w;
            base.height = girada ? w : h;
            var ctx = base.getContext('2d');
            // Primero se gira y después se voltea, igual que en el servidor.
            ctx.translate(base.width / 2, base.height / 2);
            if (estado.voltear) ctx.scale(-1, 1);
            ctx.rotate(estado.rotacion * Math.PI / 180);
            ctx.drawImage(img, -w / 2, -h / 2, w, h);
            editor.base = base;
        }

        /* --- Lienzo principal y recuadro ------------------------------- */
        var medidas = { ancho: 0, alto: 0 };

        function dibujar() {
            if (!editor.base || cuerpo.hidden) return;
            var base = editor.base;
            var disponible = lienzo.parentNode.clientWidth || 600;
            var altoMaximo = Math.max(260, Math.min(520, window.innerHeight * 0.6));
            var escala = Math.min(disponible / base.width, altoMaximo / base.height, 1.5);
            medidas.ancho = Math.round(base.width * escala);
            medidas.alto = Math.round(base.height * escala);
            var densidad = window.devicePixelRatio || 1;
            canvas.width = Math.round(medidas.ancho * densidad);
            canvas.height = Math.round(medidas.alto * densidad);
            canvas.style.width = medidas.ancho + 'px';
            canvas.style.height = medidas.alto + 'px';
            lienzo.style.width = medidas.ancho + 'px';
            lienzo.style.height = medidas.alto + 'px';
            var ctx = canvas.getContext('2d');
            ctx.filter = filtro();
            ctx.drawImage(base, 0, 0, canvas.width, canvas.height);
            ubicarRecuadro();
            dibujarVistas();
        }

        function ubicarRecuadro() {
            recorte.style.left = (estado.x * medidas.ancho) + 'px';
            recorte.style.top = (estado.y * medidas.alto) + 'px';
            recorte.style.width = (estado.ancho * medidas.ancho) + 'px';
            recorte.style.height = (estado.alto * medidas.alto) + 'px';
        }

        /* --- Vistas previas -------------------------------------------- */
        var vistas = raiz.querySelectorAll('canvas[data-vista]');
        var titulos = raiz.querySelectorAll('[data-titulo]');

        function dibujarVistas() {
            var base = editor.base;
            if (!base) return;
            // La parte recortada, en px de la foto base.
            var sx = estado.x * base.width, sy = estado.y * base.height;
            var sw = estado.ancho * base.width, sh = estado.alto * base.height;
            Array.prototype.forEach.call(vistas, function (vista) {
                var ctx = vista.getContext('2d');
                // Igual que object-fit: cover en el sitio: llena el marco
                // y recorta lo que sobra, centrado.
                var escala = Math.max(vista.width / sw, vista.height / sh);
                var vw = vista.width / escala, vh = vista.height / escala;
                ctx.clearRect(0, 0, vista.width, vista.height);
                ctx.filter = filtro();
                ctx.drawImage(base, sx + (sw - vw) / 2, sy + (sh - vh) / 2, vw, vh, 0, 0, vista.width, vista.height);
            });
            var texto = (titulo && titulo.value.trim()) || 'Título de la noticia';
            Array.prototype.forEach.call(titulos, function (t) { t.textContent = texto; });
        }
        if (titulo) titulo.addEventListener('input', dibujarVistas);

        /* --- Recorte: proporciones ------------------------------------- */
        // Una proporción en px (ancho/alto) pasada a fracciones de la foto.
        function proporcionEnFracciones() {
            return editor.proporcion * editor.base.height / editor.base.width;
        }

        function recorteMaximo() {
            // El recorte más grande con la proporción elegida, centrado.
            if (!editor.proporcion) {
                estado.x = 0; estado.y = 0; estado.ancho = 1; estado.alto = 1;
                return;
            }
            var r = proporcionEnFracciones();
            var ancho = 1, alto = 1 / r;
            if (alto > 1) { alto = 1; ancho = r; }
            estado.ancho = ancho; estado.alto = alto;
            estado.x = (1 - ancho) / 2; estado.y = (1 - alto) / 2;
        }

        var botonesProporcion = raiz.querySelectorAll('[data-proporcion]');
        function marcarProporcion() {
            Array.prototype.forEach.call(botonesProporcion, function (b) {
                var valor = b.getAttribute('data-proporcion');
                var activo = editor.proporcion ? Math.abs(parseFloat(valor) - editor.proporcion) < 0.001 : valor === 'libre';
                b.setAttribute('aria-pressed', activo ? 'true' : 'false');
            });
        }
        Array.prototype.forEach.call(botonesProporcion, function (b) {
            b.addEventListener('click', function () {
                var valor = b.getAttribute('data-proporcion');
                editor.proporcion = valor === 'libre' ? null : parseFloat(valor);
                marcarProporcion();
                if (editor.proporcion) recorteMaximo();
                cambio(false);
            });
        });

        /* --- Recorte: arrastrar y estirar ------------------------------ */
        var arrastre = null;

        function fraccionDelPuntero(evento) {
            var caja = lienzo.getBoundingClientRect();
            return {
                x: limitar((evento.clientX - caja.left) / medidas.ancho, 0, 1),
                y: limitar((evento.clientY - caja.top) / medidas.alto, 0, 1)
            };
        }

        recorte.addEventListener('pointerdown', function (evento) {
            if (evento.button !== undefined && evento.button !== 0) return;
            var asa = evento.target.getAttribute('data-asa');
            arrastre = { asa: asa, inicio: fraccionDelPuntero(evento), desde: copia(estado) };
            recorte.setPointerCapture(evento.pointerId);
            evento.preventDefault();
        });

        recorte.addEventListener('pointermove', function (evento) {
            if (!arrastre) return;
            var p = fraccionDelPuntero(evento);
            var d = arrastre.desde;
            if (!arrastre.asa) {
                // Mover el recuadro completo, sin salirse de la foto.
                estado.x = limitar(d.x + p.x - arrastre.inicio.x, 0, 1 - d.ancho);
                estado.y = limitar(d.y + p.y - arrastre.inicio.y, 0, 1 - d.alto);
            } else {
                estirar(arrastre.asa, p, d);
            }
            ubicarRecuadro();
            dibujarVistas();
        });

        function soltar() {
            if (!arrastre) return;
            arrastre = null;
            anotar();
        }
        recorte.addEventListener('pointerup', soltar);
        recorte.addEventListener('pointercancel', soltar);

        function estirar(asa, p, d) {
            // La esquina opuesta queda fija.
            var fijoX = asa.indexOf('w') >= 0 ? d.x + d.ancho : d.x;
            var fijoY = asa.indexOf('n') >= 0 ? d.y + d.alto : d.y;
            var haciaIzquierda = asa.indexOf('w') >= 0;
            var haciaArriba = asa.indexOf('n') >= 0;
            var maxAncho = haciaIzquierda ? fijoX : 1 - fijoX;
            var maxAlto = haciaArriba ? fijoY : 1 - fijoY;
            var ancho = limitar(Math.abs(p.x - fijoX), MINIMO, maxAncho);
            var alto = limitar(Math.abs(p.y - fijoY), MINIMO, maxAlto);

            if (editor.proporcion) {
                var r = proporcionEnFracciones();  // ancho = alto * r
                // Manda el lado que más se movió; el otro se ajusta.
                if (ancho / r > alto) alto = ancho / r; else ancho = alto * r;
                if (alto > maxAlto) { alto = maxAlto; ancho = alto * r; }
                if (ancho > maxAncho) { ancho = maxAncho; alto = ancho / r; }
            }
            estado.ancho = ancho;
            estado.alto = alto;
            estado.x = haciaIzquierda ? fijoX - ancho : fijoX;
            estado.y = haciaArriba ? fijoY - alto : fijoY;
        }

        /* --- Girar, voltear, ajustes ----------------------------------- */
        raiz.addEventListener('click', function (evento) {
            var boton = evento.target.closest('[data-accion]');
            if (!boton) return;
            var accion = boton.getAttribute('data-accion');
            if (accion === 'girar-der') estado.rotacion = (estado.rotacion + 90) % 360;
            if (accion === 'girar-izq') estado.rotacion = (estado.rotacion + 270) % 360;
            if (accion === 'voltear') estado.voltear = !estado.voltear;
            if (accion === 'restablecer') {
                estado = copia(POR_DEFECTO);
                editor.estado = estado;
                editor.proporcion = null;
                marcarProporcion();
                sincronizarControles();
            }
            // Girar o voltear cambia la forma de la foto: el recorte
            // vuelve a ocupar todo (o lo máximo con la proporción elegida).
            construirBase();
            recorteMaximo();
            cambio(false);
        });

        var deslizadores = raiz.querySelectorAll('input[data-ajuste]');
        function sincronizarControles() {
            Array.prototype.forEach.call(deslizadores, function (d) {
                var clave = d.getAttribute('data-ajuste');
                d.value = Math.round(estado[clave] * 100);
                raiz.querySelector('[data-salida="' + clave + '"]').textContent = d.value + '%';
            });
        }
        Array.prototype.forEach.call(deslizadores, function (d) {
            d.addEventListener('input', function () {
                var clave = d.getAttribute('data-ajuste');
                estado[clave] = parseInt(d.value, 10) / 100;
                raiz.querySelector('[data-salida="' + clave + '"]').textContent = d.value + '%';
                cambio(false);
            });
        });

        function cambio(reconstruir) {
            if (reconstruir) construirBase();
            anotar();
            dibujar();
        }

        /* --- De dónde sale la foto ------------------------------------- */
        function cargar(src) {
            var img = new Image();
            img.onload = function () {
                editor.imagen = img;
                vacio.hidden = true;
                cuerpo.hidden = false;
                construirBase();
                sincronizarControles();
                marcarProporcion();
                dibujar();
            };
            img.onerror = function () {
                cuerpo.hidden = true;
                vacio.hidden = false;
            };
            img.src = src;
        }

        // Archivo nuevo elegido en la pestaña Fotos: el editor pasa a
        // usar ese, y los ajustes de la foto anterior se descartan. Se lee
        // como data: (la CSP no permite imágenes blob:).
        if (archivo) {
            archivo.addEventListener('change', function () {
                var elegido = archivo.files && archivo.files[0];
                if (!elegido) return;
                estado = copia(POR_DEFECTO);
                editor.estado = estado;
                editor.proporcion = null;
                anotar();
                var lector = new FileReader();
                lector.onload = function () { cargar(lector.result); };
                lector.readAsDataURL(elegido);
            });
        }

        var original = raiz.getAttribute('data-original');
        if (original) cargar(original);

        editor.mostrar = function () {
            // El lienzo mide 0 mientras su pestaña está escondida: se
            // dibuja de nuevo cada vez que se abre.
            window.requestAnimationFrame(dibujar);
        };
        var espera = null;
        window.addEventListener('resize', function () {
            clearTimeout(espera);
            espera = setTimeout(dibujar, 120);
        });
        editor.listo = true;
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (!document.getElementById('noticia_form')) return;
        iniciarEditor();
        iniciarVistaPrevia();
        armarPestanas();
    });
})();
