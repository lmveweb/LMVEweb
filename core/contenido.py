"""Contenido editable del sitio que no vive en la base de datos.

Listas en Python (no en las plantillas) para que sumar o sacar un
colegio o una foto sea editar una línea acá, sin tocar HTML.
"""


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
