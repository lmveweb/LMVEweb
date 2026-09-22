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
COLEGIOS = [
    {'src': 'core/img/colegios/colegio-aleman-santiago.png', 'alt': 'Colegio Alemán Santiago'},
    {'src': 'core/img/colegios/colegio-alicante-del-valle.png', 'alt': 'Colegio Alicante del Valle'},
    {'src': 'core/img/colegios/colegio-andree-english-school.png', 'alt': 'Colegio Andrée English School'},
    {'src': 'core/img/colegios/colegio-british-royal-school.png', 'alt': 'Colegio British Royal School'},
    {'src': 'core/img/colegios/colegio-carampangue.png', 'alt': 'Colegio Carampangue'},
    {'src': 'core/img/colegios/colegio-colonial-de-pirque.png', 'alt': 'Colegio Colonial de Pirque'},
    {'src': 'core/img/colegios/colegio-cumbres.png', 'alt': 'Colegio Cumbres'},
    {'src': 'core/img/colegios/colegio-epullay-montessori.png', 'alt': 'Colegio Epullay Montessori'},
    {'src': 'core/img/colegios/colegio-hispano-americano.png', 'alt': 'Colegio Hispano Americano'},
    {'src': 'core/img/colegios/colegio-institucion-teresiana.png', 'alt': 'Colegio Institución Teresiana'},
    {'src': 'core/img/colegios/colegio-instituto-alonso-de-ercilla.png', 'alt': 'Colegio Instituto Alonso de Ercilla'},
    {'src': 'core/img/colegios/colegio-instituto-santa-maria.png', 'alt': 'Colegio Instituto Santa María'},
    {'src': 'core/img/colegios/colegio-juanita-de-los-andes.png', 'alt': 'Colegio Juanita de los Andes'},
    {'src': 'core/img/colegios/colegio-la-girouette.png', 'alt': 'Colegio La Girouette'},
    {'src': 'core/img/colegios/colegio-la-maissonette.png', 'alt': 'Colegio La Maissonette'},
    {'src': 'core/img/colegios/colegio-lincoln-international-chicureo.png', 'alt': 'Colegio Lincoln International (Chicureo)'},
    {'src': 'core/img/colegios/colegio-lincoln-lo-barnechea.png', 'alt': 'Colegio Lincoln Lo Barnechea'},
    {'src': 'core/img/colegios/colegio-marcelino-champagnat.png', 'alt': 'Colegio Marcelino Champagnat'},
    {'src': 'core/img/colegios/colegio-mariano-de-schoenstatt.png', 'alt': 'Colegio Mariano de Schoenstatt'},
    {'src': 'core/img/colegios/colegio-maria-inmaculada.png', 'alt': 'Colegio María Inmaculada'},
    {'src': 'core/img/colegios/colegio-mayor-penalolen.png', 'alt': 'Colegio Mayor Peñalolén'},
    {'src': 'core/img/colegios/colegio-mayor-tobalaba.png', 'alt': 'Colegio Mayor Tobalaba'},
    {'src': 'core/img/colegios/colegio-monte-tabor-y-nazaret.png', 'alt': 'Colegio Monte Tabor y Nazaret'},
    {'src': 'core/img/colegios/colegio-notre-dame.png', 'alt': 'Colegio Notre Dame'},
    {'src': 'core/img/colegios/colegio-pedro-de-valdivia-penalolen.png', 'alt': 'Colegio Pedro de Valdivia Peñalolén'},
    {'src': 'core/img/colegios/colegio-sscc-providencia.png', 'alt': 'Colegio SSCC Providencia'},
    {'src': 'core/img/colegios/colegio-sagrado-corazon-talagante.png', 'alt': 'Colegio Sagrado Corazón Talagante'},
    {'src': 'core/img/colegios/colegio-san-felipe-diacono.png', 'alt': 'Colegio San Felipe Diácono'},
    {'src': 'core/img/colegios/colegio-san-ignacio-alonso-ovalle.png', 'alt': 'Colegio San Ignacio Alonso Ovalle'},
    {'src': 'core/img/colegios/colegio-san-ignacio-el-bosque.png', 'alt': 'Colegio San Ignacio el Bosque'},
    {'src': 'core/img/colegios/colegio-san-jose-de-chicureo.png', 'alt': 'Colegio San José de Chicureo'},
    {'src': 'core/img/colegios/colegio-san-nicolas-diacono.png', 'alt': 'Colegio San Nicolás Diacono'},
    {'src': 'core/img/colegios/colegio-san-pedro-nolasco.png', 'alt': 'Colegio San Pedro Nolasco'},
    {'src': 'core/img/colegios/colegio-santa-cruz-de-chicureo.png', 'alt': 'Colegio Santa Cruz de Chicureo'},
    {'src': 'core/img/colegios/colegio-santa-maria-lo-canas.png', 'alt': 'Colegio Santa María Lo Cañas'},
    {'src': 'core/img/colegios/colegio-scuola-italiana.png', 'alt': 'Colegio Scuola Italiana'},
    {'src': 'core/img/colegios/colegio-sek-internacional-chile.png', 'alt': 'Colegio Sek Internacional Chile'},
    {'src': 'core/img/colegios/colegio-suizo-de-santiago.png', 'alt': 'Colegio Suizo de Santiago'},
    {'src': 'core/img/colegios/colegio-the-english-institute.png', 'alt': 'Colegio The English Institute'},
    {'src': 'core/img/colegios/colegio-the-southern-cross-school.png', 'alt': 'Colegio The Southern Cross School'},
    {'src': 'core/img/colegios/colegio-thomas-morus.png', 'alt': 'Colegio Thomas Morus'},
    {'src': 'core/img/colegios/liceo-alianza-francesa.png', 'alt': 'Liceo Alianza Francesa'},
    {'src': 'core/img/colegios/liceo-camilo-ortuzar-montt.png', 'alt': 'Liceo Camilo Ortúzar Montt'},
    {'src': 'core/img/colegios/liceo-manuel-de-salas.png', 'alt': 'Liceo Manuel de Salas'},
    {'src': 'core/img/colegios/liceo-nacional-maipu.png', 'alt': 'Liceo Nacional Maipú'},
    {'src': 'core/img/colegios/liceo-salesiano-manuel-arriaran-barros.jpeg', 'alt': 'Liceo Salesiano Manuel Arriaran Barros'},
    {'src': 'core/img/colegios/the-grange-school.png', 'alt': 'The Grange School'},
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
