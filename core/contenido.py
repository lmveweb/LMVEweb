"""Contenido editable del sitio que no vive en la base de datos.

Listas en Python (no en las plantillas) para que sumar o sacar un
colegio, una foto o un evento sea editar una línea acá, sin tocar HTML.
"""

from datetime import date

from django.utils import timezone

# Evento destacado de la portada.
#
# Se muestra solo hasta el día de cierre inclusive: pasada esa fecha
# desaparece solo, sin que nadie tenga que acordarse de sacarlo del
# sitio (ver evento_vigente). Para bajarlo antes de tiempo, basta con
# dejar EVENTO_DESTACADO = None; para el próximo torneo, reemplazar los
# datos de acá.
#
# Los nombres de los colegios van tal como los publicó la Liga en el
# flyer oficial, sin completarlos ni corregirlos.
EVENTO_DESTACADO = {
    'nombre': 'Copa Milled 2026',
    'inicio': date(2026, 9, 25),
    'fin': date(2026, 9, 27),
    # Texto para mostrar; los números van aparte para el bloque grande
    # de la fecha, que los luce como en el flyer.
    'dias': '25, 26 y 27 de septiembre',
    'dias_numeros': '25 · 26 · 27',
    'mes': 'Septiembre 2026',
    'sede': 'British Royal School',
    'direccion': 'Las Perdices #263, La Reina',
    'comuna': 'La Reina',
    # Lo que se le manda a Google Maps al tocar la dirección. Va aparte
    # de 'direccion' a propósito: sin el "#" (Maps ubica mejor "263" que
    # "#263") y con ciudad y país, para que no confunda la calle con una
    # de otra comuna o de otro país.
    'mapa_query': 'British Royal School, Las Perdices 263, La Reina, Santiago, Chile',
    # Afiche oficial. La versión de la página está achicada a 760 px de
    # ancho (96 KB en WebP); la completa es el original, y se abre solo
    # si alguien hace clic para leer la letra chica.
    'afiche': 'core/img/eventos/copa-milled-2026.webp',
    'afiche_completo': 'core/img/eventos/copa-milled-2026-completo.webp',
    'afiche_alt': (
        'Afiche de la Copa Milled 2026: 25, 26 y 27 de septiembre en el '
        'British Royal School, Las Perdices #263, La Reina.'
    ),
    # "Colegio" antepuesto a cada nombre (el flyer lo omite porque ya
    # viene bajo el subtítulo "Colegios en competencia"), salvo los que
    # ya llevan su propio tipo de institución (Liceo, Instituto, School).
    # Manuel de Salas y Alianza Francesa Viña del Mar quedan como Liceo
    # (no Colegio) porque así están registrados en COLEGIOS más arriba
    # para ese mismo tipo de institución.
    'damas': [
        'Colegio Suizo',
        'Colegio Andrée',
        'Colegio Thomas Morus',
        'British Royal School',
        'Colegio Alemán de Santiago',
        'Colegio Pedro de Valdivia Peñalolén',
        'Liceo Alianza Francesa Viña del Mar',
        'Colegio San Luis de Alba (Valdivia)',
        'Colegio Sagrado Corazón de Talagante',
        'Liceo Manuel de Salas',
    ],
    'varones': [
        'Colegio Suizo',
        'Liceo Nacional de Maipú',
        'Colegio Thomas Morus',
        'Instituto Alonso de Ercilla',
        'Colegio Don Orione Maipú',
        'Colegio Pedro de Valdivia Peñalolén',
        'Colegio Mary Graham (Villa Alemana)',
        'Colegio Andrés Bello Pampa (La Serena)',
        'Colegio SSCC Viña del Mar',
        'Colegio Santa María de Lo Cañas',
    ],
}


def evento_vigente(hoy=None):
    """El evento destacado mientras no haya terminado, con la etiqueta de
    cuenta regresiva ya resuelta. None si ya pasó (o si no hay evento).

    La fecha se calcula en la zona horaria del proyecto (America/Santiago),
    no en UTC: si no, entre las 21:00 y la medianoche de Chile el sitio
    ya estaría contando un día de más.

    `hoy` existe para que los tests puedan pararse en cualquier fecha sin
    depender del reloj real ni de una dependencia extra.
    """
    if not EVENTO_DESTACADO:
        return None

    hoy = hoy or timezone.localdate()
    if hoy > EVENTO_DESTACADO['fin']:
        return None

    faltan = (EVENTO_DESTACADO['inicio'] - hoy).days
    if faltan > 1:
        etiqueta = f'Faltan {faltan} días'
    elif faltan == 1:
        etiqueta = 'Falta 1 día'
    elif faltan == 0:
        etiqueta = '¡Es hoy!'
    else:
        etiqueta = '¡En curso!'

    return {**EVENTO_DESTACADO, 'etiqueta': etiqueta}


# Colegios que compiten en la Liga, para el carrusel de Inicio.
# Para sumar uno: deja su logo (PNG o JPG) en core/static/core/img/colegios/,
# agrega su línea acá con esa extensión y corre
# scripts/optimizar_imagenes.py: lo pasa a WebP y completa ancho/alto.
COLEGIOS = [
    {'src': 'core/img/colegios/colegio-aleman-santiago.webp', 'alt': 'Colegio Alemán Santiago', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-alicante-del-valle.webp', 'alt': 'Colegio Alicante del Valle', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-andree-english-school.webp', 'alt': 'Colegio Andrée English School', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-british-royal-school.webp', 'alt': 'Colegio British Royal School', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-carampangue.webp', 'alt': 'Colegio Carampangue', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-colonial-de-pirque.webp', 'alt': 'Colegio Colonial de Pirque', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-cumbres.webp', 'alt': 'Colegio Cumbres', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-epullay-montessori.webp', 'alt': 'Colegio Epullay Montessori', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-hispano-americano.webp', 'alt': 'Colegio Hispano Americano', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-institucion-teresiana.webp', 'alt': 'Colegio Institución Teresiana', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-instituto-alonso-de-ercilla.webp', 'alt': 'Colegio Instituto Alonso de Ercilla', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-instituto-santa-maria.webp', 'alt': 'Colegio Instituto Santa María', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-juanita-de-los-andes.webp', 'alt': 'Colegio Juanita de los Andes', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-la-girouette.webp', 'alt': 'Colegio La Girouette', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-la-maissonette.webp', 'alt': 'Colegio La Maissonette', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-lincoln-international-chicureo.webp', 'alt': 'Colegio Lincoln International (Chicureo)', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-lincoln-lo-barnechea.webp', 'alt': 'Colegio Lincoln Lo Barnechea', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-marcelino-champagnat.webp', 'alt': 'Colegio Marcelino Champagnat', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-mariano-de-schoenstatt.webp', 'alt': 'Colegio Mariano de Schoenstatt', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-maria-inmaculada.webp', 'alt': 'Colegio María Inmaculada', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-mayor-penalolen.webp', 'alt': 'Colegio Mayor Peñalolén', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-mayor-tobalaba.webp', 'alt': 'Colegio Mayor Tobalaba', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-monte-tabor-y-nazaret.webp', 'alt': 'Colegio Monte Tabor y Nazaret', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-notre-dame.webp', 'alt': 'Colegio Notre Dame', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-pedro-de-valdivia-penalolen.webp', 'alt': 'Colegio Pedro de Valdivia Peñalolén', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-sscc-providencia.webp', 'alt': 'Colegio SSCC Providencia', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-sagrado-corazon-talagante.webp', 'alt': 'Colegio Sagrado Corazón Talagante', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-san-felipe-diacono.webp', 'alt': 'Colegio San Felipe Diácono', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-san-ignacio-alonso-ovalle.webp', 'alt': 'Colegio San Ignacio Alonso Ovalle', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-san-ignacio-el-bosque.webp', 'alt': 'Colegio San Ignacio el Bosque', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-san-jose-de-chicureo.webp', 'alt': 'Colegio San José de Chicureo', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-san-nicolas-diacono.webp', 'alt': 'Colegio San Nicolás Diacono', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-san-pedro-nolasco.webp', 'alt': 'Colegio San Pedro Nolasco', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-santa-cruz-de-chicureo.webp', 'alt': 'Colegio Santa Cruz de Chicureo', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-santa-maria-lo-canas.webp', 'alt': 'Colegio Santa María Lo Cañas', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-scuola-italiana.webp', 'alt': 'Colegio Scuola Italiana', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-sek-internacional-chile.webp', 'alt': 'Colegio Sek Internacional Chile', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-suizo-de-santiago.webp', 'alt': 'Colegio Suizo de Santiago', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-the-english-institute.webp', 'alt': 'Colegio The English Institute', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-the-southern-cross-school.webp', 'alt': 'Colegio The Southern Cross School', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/colegio-thomas-morus.webp', 'alt': 'Colegio Thomas Morus', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/liceo-alianza-francesa.webp', 'alt': 'Liceo Alianza Francesa', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/liceo-camilo-ortuzar-montt.webp', 'alt': 'Liceo Camilo Ortúzar Montt', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/liceo-manuel-de-salas.webp', 'alt': 'Liceo Manuel de Salas', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/liceo-nacional-maipu.webp', 'alt': 'Liceo Nacional Maipú', 'ancho': 160, 'alto': 200},
    {'src': 'core/img/colegios/liceo-salesiano-manuel-arriaran-barros.webp', 'alt': 'Liceo Salesiano Manuel Arriaran Barros', 'ancho': 158, 'alto': 200},
    {'src': 'core/img/colegios/the-grange-school.webp', 'alt': 'The Grange School', 'ancho': 160, 'alto': 200},
]


# Fotos de la galería de Multimedia.
FOTOS_MULTIMEDIA = [
    {'src': 'core/img/fotos/galeria-1.jpg', 'alt': 'Armado en zona de red durante un partido de la Liga'},
    {'src': 'core/img/fotos/galeria-2.jpg', 'alt': 'Bloqueo en la red durante un partido de la Liga'},
    {'src': 'core/img/fotos/galeria-3.jpg', 'alt': 'Saque de salto durante un partido de la Liga'},
    {'src': 'core/img/fotos/impacto-reconocimiento.jpg', 'alt': 'Ceremonia de reconocimiento a colaboradores de la Liga'},
    {'src': 'core/img/fotos/galeria-4.jpg', 'alt': 'Remate durante una jornada de competencia'},
    {'src': 'core/img/fotos/archivo-hoy-2.jpg', 'alt': 'Disputa de balón sobre la red'},
    {'src': 'core/img/fotos/archivo-hoy-5.jpg', 'alt': 'Remate frente al bloqueo rival'},
    {'src': 'core/img/fotos/archivo-jornada-2.jpg', 'alt': 'Equipos formados en cancha durante una ceremonia'},
    {'src': 'core/img/fotos/archivo-jornada-3.jpg', 'alt': 'Equipos posando junto a la red al término de una jornada'},
    {'src': 'core/img/fotos/archivo-jornada-1.jpg', 'alt': 'Presentación de los colegios participantes'},
    {'src': 'core/img/fotos/impacto-banner-sponsor.jpg', 'alt': 'Plantel completo en un recinto de la Liga'},
    {'src': 'core/img/fotos/archivo-hoy-1.jpg', 'alt': 'Trofeos y balones preparados para la premiación'},
    {'src': 'core/img/fotos/historia-1987.jpg', 'alt': 'Equipo de la Liga a fines de los años 80'},
    {'src': 'core/img/fotos/archivo-80s-2.jpg', 'alt': 'Equipo junto a su profesor, década de 1980'},
    {'src': 'core/img/fotos/archivo-90s-seleccion.jpg', 'alt': 'Selección de la Liga, 1990'},
]

# Tanda de fotos recientes (jornadas 2026) sumada más adelante: sin
# contexto de fecha/colegio/categoría por foto todavía, así que llevan
# alt genérico. Cuando haya esa información, lo ideal es reemplazar
# este bloque por entradas explícitas como las de arriba.
FOTOS_MULTIMEDIA += [
    {'src': f'core/img/fotos/galeria-{i}.jpg', 'alt': 'Fotografía de un partido de la Liga'}
    for i in range(5, 58)
]
