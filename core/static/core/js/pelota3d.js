/*
 * Pelota 3D de la LMVE — componente reutilizable.
 *
 * Balón de voleibol genérico de 18 paneles, en los colores de la Liga
 * y con el wordmark "LMVE". Los 18 paneles salen de un cubo inflado a
 * esfera: 6 caras × 3 tiras paralelas cada una, con las tiras de
 * caras vecinas perpendiculares entre sí. Esa perpendicularidad es lo
 * que hace que se lea como pelota de voleibol y no como globo
 * aerostático (que es lo que pasa con gajos verticales de polo a polo).
 *
 * El color no se decide con la coordenada 2D de la textura, sino
 * reconstruyendo la dirección 3D (x,y,z) de cada punto sobre la esfera
 * y preguntando en qué cara del cubo y en qué tercio de esa cara cae.
 *
 * Para que no se vea plana se generan tres mapas, no uno:
 *   - color:     paneles + suciedad + mugre acumulada en las costuras
 *   - relieve:   costuras hundidas de verdad + micro-textura de cuero
 *   - rugosidad: las costuras y las zonas gastadas reflejan distinto
 *                que el panel limpio
 * Las costuras salen de una transformada de distancia sobre el mapa de
 * paneles, así el hundido, la mugre y el cambio de brillo calzan todos
 * en el mismo lugar por construcción.
 *
 * El wordmark va pegado al ecuador, sobre la tira central de la cara
 * que mira a la cámara: es la zona con menos distorsión de la textura
 * (cerca de los polos la curvatura aplasta cualquier letra).
 *
 * Requiere que Three.js (r128) ya esté cargado en la página.
 *
 * Uso:
 *   crearPelotaLMVE(document.getElementById('miPelota'), {
 *       velocidad: 0.0016  // opcional, radianes por frame
 *   });
 */
(function () {
    'use strict';

    // Generar los mapas cuesta (ruido 3D + transformada de distancia) y
    // no depende de la instancia: se calculan una sola vez y se comparten
    // entre todas las pelotas de la página. Se cachean los <canvas>, no
    // las texturas de Three.js, porque cada pelota tiene su propio
    // renderer y conviene que cada uno maneje su propia textura.
    var lienzosCache = null;

    function hexARgb(hex) {
        var n = parseInt(hex.slice(1), 16);
        return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
    }

    function limitar(v, min, max) {
        return v < min ? min : (v > max ? max : v);
    }

    /* ---------------- ruido de valor 3D ----------------
       Se muestrea con la dirección 3D del punto (no con la coordenada
       de la textura) para que el grano no se estire cerca de los polos. */
    function hash3(i, j, k) {
        var n = (Math.imul(i, 73856093) ^ Math.imul(j, 19349663) ^ Math.imul(k, 83492791)) >>> 0;
        n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
        return ((n ^ (n >>> 16)) >>> 0) / 4294967296;
    }

    function suavizar(t) { return t * t * (3 - 2 * t); }

    function ruido3(x, y, z) {
        var i = Math.floor(x), j = Math.floor(y), k = Math.floor(z);
        var fx = suavizar(x - i), fy = suavizar(y - j), fz = suavizar(z - k);
        var c000 = hash3(i, j, k), c100 = hash3(i + 1, j, k);
        var c010 = hash3(i, j + 1, k), c110 = hash3(i + 1, j + 1, k);
        var c001 = hash3(i, j, k + 1), c101 = hash3(i + 1, j, k + 1);
        var c011 = hash3(i, j + 1, k + 1), c111 = hash3(i + 1, j + 1, k + 1);
        var x00 = c000 + (c100 - c000) * fx, x10 = c010 + (c110 - c010) * fx;
        var x01 = c001 + (c101 - c001) * fx, x11 = c011 + (c111 - c011) * fx;
        var y0 = x00 + (x10 - x00) * fy, y1 = x01 + (x11 - x01) * fy;
        return y0 + (y1 - y0) * fz;
    }

    /* Dirección 3D de un punto de la textura, con la convención UV de
       SphereGeometry: la fila de arriba del canvas es el polo norte. */
    function tablasDireccion(W, H) {
        var cosPhi = new Float32Array(W), sinPhi = new Float32Array(W);
        for (var x = 0; x < W; x++) {
            var phi = (x / W) * Math.PI * 2;
            cosPhi[x] = Math.cos(phi);
            sinPhi[x] = Math.sin(phi);
        }
        var cosT = new Float32Array(H), sinT = new Float32Array(H);
        for (var y = 0; y < H; y++) {
            var theta = (y / H) * Math.PI;
            cosT[y] = Math.cos(theta);
            sinT[y] = Math.sin(theta);
        }
        return { cosPhi: cosPhi, sinPhi: sinPhi, cosT: cosT, sinT: sinT };
    }

    /* A qué panel (cara*3 + tira) pertenece una dirección. El entramado
       va girado 90° en X respecto de la esfera para que la cara que mira
       a la cámara tenga sus tiras HORIZONTALES: el wordmark es
       horizontal y así entra completo en una sola tira, sin cruzar una
       costura. */
    function panelDe(dx, dy, dz) {
        var rx = dx, ry = dz, rz = -dy;
        var ax = Math.abs(rx), ay = Math.abs(ry), az = Math.abs(rz);
        var cara, s;
        if (ax >= ay && ax >= az) {
            cara = rx > 0 ? 0 : 1;
            s = ry / ax;   // las tiras de ±x se cortan según y
        } else if (ay >= az) {
            cara = ry > 0 ? 2 : 3;
            s = rz / ay;   // las de ±y, según z
        } else {
            cara = rz > 0 ? 4 : 5;
            s = rx / az;   // las de ±z, según x
        }
        var tira = s < -1 / 3 ? 0 : (s < 1 / 3 ? 1 : 2);
        return cara * 3 + tira;
    }

    /* Distancia (en píxeles) de cada punto a la costura más cercana,
       por chamfer en dos barridos. Mucho más barato que medir a mano y
       da un degradado suave que sirve para hundir, ensuciar y opacar la
       costura de forma coherente. */
    function distanciaACostura(idPanel, W, H) {
        var INF = 1e9;
        var dist = new Float32Array(W * H);
        for (var y = 0; y < H; y++) {
            for (var x = 0; x < W; x++) {
                var i = y * W + x, id = idPanel[i];
                var borde =
                    idPanel[y * W + (x + 1) % W] !== id ||
                    idPanel[y * W + (x - 1 + W) % W] !== id ||
                    (y > 0 && idPanel[i - W] !== id) ||
                    (y < H - 1 && idPanel[i + W] !== id);
                dist[i] = borde ? 0 : INF;
            }
        }
        var D1 = 1, D2 = 1.41421356;
        for (var y = 0; y < H; y++) {
            for (var x = 0; x < W; x++) {
                var i = y * W + x, d = dist[i];
                var xl = (x - 1 + W) % W, xr = (x + 1) % W;
                var v = dist[y * W + xl] + D1; if (v < d) d = v;
                if (y > 0) {
                    v = dist[(y - 1) * W + x] + D1; if (v < d) d = v;
                    v = dist[(y - 1) * W + xl] + D2; if (v < d) d = v;
                    v = dist[(y - 1) * W + xr] + D2; if (v < d) d = v;
                }
                dist[i] = d;
            }
        }
        for (var y = H - 1; y >= 0; y--) {
            for (var x = W - 1; x >= 0; x--) {
                var i = y * W + x, d = dist[i];
                var xl = (x - 1 + W) % W, xr = (x + 1) % W;
                var v = dist[y * W + xr] + D1; if (v < d) d = v;
                if (y < H - 1) {
                    v = dist[(y + 1) * W + x] + D1; if (v < d) d = v;
                    v = dist[(y + 1) * W + xl] + D2; if (v < d) d = v;
                    v = dist[(y + 1) * W + xr] + D2; if (v < d) d = v;
                }
                dist[i] = d;
            }
        }
        return dist;
    }

    /* Muestreo bilineal de una grilla de ruido, con vuelta horizontal.
       Permite calcular el ruido a resolución baja (que es lo caro) y
       usarlo a resolución alta sin que se noten los escalones. */
    function muestrear(grid, gw, gh, u, v) {
        var fx = u * gw - 0.5, fy = v * gh - 0.5;
        var x0 = Math.floor(fx), y0 = Math.floor(fy);
        var tx = fx - x0, ty = fy - y0;
        var x1 = ((x0 + 1) % gw + gw) % gw;
        x0 = ((x0 % gw) + gw) % gw;
        var y1 = limitar(y0 + 1, 0, gh - 1);
        y0 = limitar(y0, 0, gh - 1);
        var a = grid[y0 * gw + x0], b = grid[y0 * gw + x1];
        var c = grid[y1 * gw + x0], d = grid[y1 * gw + x1];
        var ab = a + (b - a) * tx, cd = c + (d - c) * tx;
        return ab + (cd - ab) * ty;
    }

    function grillaRuido(gw, gh, frecuencia, semilla) {
        var g = new Float32Array(gw * gh);
        var t = tablasDireccion(gw, gh);
        for (var y = 0; y < gh; y++) {
            var sT = t.sinT[y], cT = t.cosT[y];
            for (var x = 0; x < gw; x++) {
                var dx = -t.cosPhi[x] * sT, dy = cT, dz = t.sinPhi[x] * sT;
                g[y * gw + x] = ruido3(
                    dx * frecuencia + semilla,
                    dy * frecuencia + semilla * 1.7,
                    dz * frecuencia + semilla * 2.3
                );
            }
        }
        return g;
    }

    function crearLienzos() {
        // El mapa de color va al doble de resolución que los otros dos
        // porque es el único que lleva el wordmark, que sí necesita
        // definición. Relieve y rugosidad no llevan texto: a la mitad
        // se ven igual y ahorran memoria y tiempo.
        var W = 2048, H = 1024;
        var MW = W >> 1, MH = H >> 1;

        var CARAS = [
            hexARgb('#F2A413'), // +x  ámbar
            hexARgb('#F2620F'), // -x  naranjo
            hexARgb('#ffffff'), // +y  blanco  ← cara que mira a la cámara
            hexARgb('#163E73'), // -y  azul marino
            hexARgb('#ffffff'), // +z  blanco (abajo)
            hexARgb('#D70A18')  // -z  rojo (arriba)
        ];

        var tabla = tablasDireccion(W, H);
        var idPanel = new Int32Array(W * H);
        for (var y = 0; y < H; y++) {
            var sT = tabla.sinT[y], cT = tabla.cosT[y];
            for (var x = 0; x < W; x++) {
                var dx = -tabla.cosPhi[x] * sT;
                var dz = tabla.sinPhi[x] * sT;
                idPanel[y * W + x] = panelDe(dx, cT, dz);
            }
        }
        var dist = distanciaACostura(idPanel, W, H);

        // Grano fino del cuero y manchones de uso. El grano se calcula a
        // resolución media y se interpola; los manchones son de baja
        // frecuencia, así que con una grilla chica alcanza y sobra.
        //
        // La frecuencia del grano NO se puede subir libremente: el ruido
        // se muestrea recorriendo la esfera, y sobre el ecuador la
        // dirección traza un círculo de radio igual a la frecuencia, o
        // sea 2π·frecuencia celdas de ruido repartidas en GRANO_W
        // muestras. Con 190 daban 1194 celdas sobre 1024 muestras: menos
        // de una muestra por celda, menos de la mitad de lo que exige
        // Nyquist. El grano suave que se buscaba salía submuestreado y
        // colapsaba en moteado aleatorio píxel a píxel — de ahí que la
        // pelota se leyera porosa, como hormigón, en vez de como cuero.
        // Con 60 quedan ~2,7 muestras por celda y el grano vuelve a ser
        // una ondulación continua.
        var GRANO_W = 1024, GRANO_H = 512;
        var grano = grillaRuido(GRANO_W, GRANO_H, 60, 3.1);
        var MUGRE_W = 256, MUGRE_H = 128;
        var mugre = grillaRuido(MUGRE_W, MUGRE_H, 3.4, 11.7);

        /* ---------- mapa de color ---------- */
        var cColor = document.createElement('canvas');
        cColor.width = W; cColor.height = H;
        var ctxColor = cColor.getContext('2d');
        var imgColor = ctxColor.createImageData(W, H);
        var ANCHO_COSTURA = 9;      // px hasta donde llega el hundido
        var SOMBRA = [12, 22, 38];  // color al que tiende la mugre de la costura

        for (var y = 0; y < H; y++) {
            for (var x = 0; x < W; x++) {
                var i = y * W + x;
                var base = CARAS[(idPanel[i] / 3) | 0];
                var d = dist[i];
                // Perfil de la costura: 1 justo encima, 0 al alejarse.
                var g = d >= ANCHO_COSTURA ? 0 : Math.pow(1 - d / ANCHO_COSTURA, 1.6);
                // La mugre se acumula en el surco, no en el panel plano.
                var oscurecer = g * 0.62;
                var idx = i * 4;
                for (var ch = 0; ch < 3; ch++) {
                    imgColor.data[idx + ch] = Math.round(
                        base[ch] * (1 - oscurecer) + SOMBRA[ch] * oscurecer
                    );
                }
                imgColor.data[idx + 3] = 255;
            }
        }
        ctxColor.putImageData(imgColor, 0, 0);

        // Capa de suciedad encima, en multiply: manchones suaves de uso,
        // más marcados en unas zonas que en otras. Se dibuja desde un
        // canvas chico escalado, que es mucho más barato que recorrer
        // los 2 millones de píxeles del mapa grande.
        var cMugre = document.createElement('canvas');
        cMugre.width = MUGRE_W; cMugre.height = MUGRE_H;
        var ctxMugre = cMugre.getContext('2d');
        var imgMugre = ctxMugre.createImageData(MUGRE_W, MUGRE_H);
        for (var i = 0; i < MUGRE_W * MUGRE_H; i++) {
            var m = mugre[i];
            // Solo la mitad más "sucia" del ruido deja marca; el resto
            // queda blanco (o sea, no altera el color al multiplicar).
            // Suave: es un balón en uso, no uno abandonado a la
            // intemperie, y el manchón fuerte sumaba al aire de cemento.
            var v = m < 0.5 ? 255 - (0.5 - m) * 80 : 255;
            var idx = i * 4;
            imgMugre.data[idx] = v;
            imgMugre.data[idx + 1] = v;
            imgMugre.data[idx + 2] = v * 0.985;  // la mugre tira a cálido
            imgMugre.data[idx + 3] = 255;
        }
        ctxMugre.putImageData(imgMugre, 0, 0);
        ctxColor.save();
        ctxColor.globalCompositeOperation = 'multiply';
        ctxColor.globalAlpha = 0.28;
        ctxColor.drawImage(cMugre, 0, 0, W, H);
        ctxColor.restore();

        // Wordmark, al final para que quede sobre la suciedad.
        var cx = W * 0.25, cy = H * 0.5;
        ctxColor.font = 'italic 900 120px Arial, Helvetica, sans-serif';
        ctxColor.textAlign = 'center';
        ctxColor.textBaseline = 'middle';
        ctxColor.lineJoin = 'round';
        ctxColor.lineWidth = 18;
        ctxColor.strokeStyle = '#ffffff';
        ctxColor.strokeText('LMVE', cx, cy);
        ctxColor.fillStyle = '#163E73';
        ctxColor.fillText('LMVE', cx, cy);

        /* ---------- relieve y rugosidad ---------- */
        var cRelieve = document.createElement('canvas');
        cRelieve.width = MW; cRelieve.height = MH;
        var ctxRelieve = cRelieve.getContext('2d');
        var imgRelieve = ctxRelieve.createImageData(MW, MH);

        var cRug = document.createElement('canvas');
        cRug.width = MW; cRug.height = MH;
        var ctxRug = cRug.getContext('2d');
        var imgRug = ctxRug.createImageData(MW, MH);

        for (var y = 0; y < MH; y++) {
            var v = (y + 0.5) / MH;
            for (var x = 0; x < MW; x++) {
                var u = (x + 0.5) / MW;
                var i = y * MW + x;
                // El mapa de distancia está al doble de resolución.
                var d = dist[(y << 1) * W + (x << 1)] * 0.5;
                var g = d >= ANCHO_COSTURA / 2 ? 0 : Math.pow(1 - d / (ANCHO_COSTURA / 2), 1.6);

                var gr = muestrear(grano, GRANO_W, GRANO_H, u, v);
                var mu = muestrear(mugre, MUGRE_W, MUGRE_H, u, v);
                var gastado = mu < 0.5 ? (0.5 - mu) * 2 : 0;

                // Relieve: SOLO las costuras. El panel va perfectamente
                // liso a propósito.
                //
                // Cualquier ruido en el relieve termina mal a esta
                // escala, y en las dos direcciones: submuestreado da
                // estática (la superficie porosa de cemento), y bien
                // muestreado da bollos redondos regulares, que es
                // exactamente el hoyuelo de una pelota de golf. En un
                // balón de indoor real el grano del sintético es tan
                // fino que a este tamaño no se ve como geometría: no
                // deforma la silueta del reflejo, solo lo vuelve un
                // poco más difuso. Por eso la variación de superficie
                // se mueve entera al mapa de rugosidad, más abajo, que
                // cambia cómo se dispersa la luz sin inventar relieve.
                var altura = 0.72 - g * 0.72;
                var hv = Math.round(limitar(altura, 0, 1) * 255);

                // Rugosidad: el surco y las zonas gastadas rebotan la
                // luz más difusa que el panel limpio. Acá sí entra el
                // grano, porque en este mapa no crea geometría: solo
                // hace que el brillo no sea uniforme como el de un
                // plástico recién moldeado. La base baja de nuevo: el
                // sintético de un balón de indoor es claramente
                // satinado, con un reflejo suave y ancho.
                var rug = 0.28 + g * 0.38 + gastado * 0.08 + (gr - 0.5) * 0.05;
                var rv = Math.round(limitar(rug, 0, 1) * 255);

                var idx = i * 4;
                imgRelieve.data[idx] = hv;
                imgRelieve.data[idx + 1] = hv;
                imgRelieve.data[idx + 2] = hv;
                imgRelieve.data[idx + 3] = 255;
                imgRug.data[idx] = rv;
                imgRug.data[idx + 1] = rv;
                imgRug.data[idx + 2] = rv;
                imgRug.data[idx + 3] = 255;
            }
        }
        ctxRelieve.putImageData(imgRelieve, 0, 0);
        ctxRug.putImageData(imgRug, 0, 0);

        return { color: cColor, relieve: cRelieve, rugosidad: cRug };
    }

    function obtenerLienzos() {
        if (!lienzosCache) lienzosCache = crearLienzos();
        return lienzosCache;
    }

    window.crearPelotaLMVE = function (mount, opts) {
        opts = opts || {};
        if (!mount || typeof THREE === 'undefined') return;

        var size = mount.clientWidth;
        if (!size) return;

        var sinMovimiento = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        var velocidad = opts.velocidad || 0.0016;

        var lienzos = obtenerLienzos();

        var scene = new THREE.Scene();
        // Encuadre ajustado: con la cámara lejos (45° a z=62) la esfera
        // ocupaba apenas la mitad del canvas y quedaba un marco
        // transparente enorme alrededor. Eso hacía que la pelota se
        // viera desalineada respecto de cualquier cosa apoyada en el
        // borde del elemento. Con 35° a z=47 la esfera llena ~95% del
        // cuadro, así el borde visible coincide con el del canvas y la
        // perspectiva sigue siendo suave (un lente más corto y cerca
        // deformaría la pelota).
        var camera = new THREE.PerspectiveCamera(35, 1, 0.1, 1000);
        camera.position.z = 47;

        var renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setSize(size, size);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        mount.appendChild(renderer.domElement);

        var maxAniso = renderer.capabilities.getMaxAnisotropy();
        function textura(lienzo) {
            var t = new THREE.CanvasTexture(lienzo);
            // Sin esto la textura se ve lavada justo en los bordes de la
            // esfera, que es donde más se comprime.
            t.anisotropy = maxAniso;
            t.needsUpdate = true;
            return t;
        }

        var ball = new THREE.Mesh(
            new THREE.SphereGeometry(14, 96, 96),
            new THREE.MeshPhysicalMaterial({
                map: textura(lienzos.color),
                bumpMap: textura(lienzos.relieve),
                // El mapa de relieve ahora solo trae costuras, así que
                // este valor únicamente define qué tan marcado es el
                // surco: no hay grano al que amplificarle la sombra.
                bumpScale: 0.5,
                roughnessMap: textura(lienzos.rugosidad),
                // La rugosidad real la pone el mapa; acá va en 1 para no
                // recortarlo (Three.js multiplica uno por otro).
                roughness: 1.0,
                metalness: 0.0,
                // Barniz claramente presente: un balón de indoor es un
                // sintético satinado y ese reflejo suave y ancho es
                // justamente lo que lo delata como pelota. Casi sin
                // barniz —como estaba— la superficie quedaba mate y
                // pétrea, que era la otra mitad del efecto hormigón.
                // Con el panel ya liso, este reflejo pasa a ser la
                // señal principal de que la superficie es sintética.
                clearcoat: 0.6,
                clearcoatRoughness: 0.18
            })
        );

        // Inclinación fija para que el gráfico se lea de frente.
        ball.rotation.x = -0.18;
        scene.add(ball);

        // Luz de estudio: una principal marcada que deja un terminador
        // suave, un relleno frío del lado opuesto para que la sombra no
        // se cierre en negro, y un contraluz que despega la silueta del
        // fondo azul de la página.
        scene.add(new THREE.HemisphereLight(0xdfe9f5, 0x16283f, 0.5));
        var principal = new THREE.DirectionalLight(0xffffff, 1.05);
        principal.position.set(-16, 20, 26);
        scene.add(principal);
        var relleno = new THREE.DirectionalLight(0xbcd2f0, 0.3);
        relleno.position.set(22, -8, 14);
        scene.add(relleno);
        var contraluz = new THREE.DirectionalLight(0xffd9a8, 0.5);
        contraluz.position.set(10, 12, -26);
        scene.add(contraluz);

        function ajustarTamano() {
            var s = mount.clientWidth;
            if (!s) return;
            renderer.setSize(s, s);
            camera.updateProjectionMatrix();
        }
        window.addEventListener('resize', ajustarTamano);

        if (sinMovimiento) {
            renderer.render(scene, camera);
            return;
        }

        // Giro lento sobre un solo eje. Sin seguimiento del cursor y sin
        // acople al scroll: son los dos gatillantes principales de vértigo.
        function animate() {
            requestAnimationFrame(animate);
            ball.rotation.y += velocidad;
            renderer.render(scene, camera);
        }
        animate();
    };
})();
