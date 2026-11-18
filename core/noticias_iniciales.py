"""Las noticias con que se estrena la sección, para que no parta vacía.

Las carga el comando cargar_noticias_iniciales (una vez, en producción
y en local). Después se editan desde el panel como cualquier otra: este
archivo no se vuelve a leer.

El cuerpo usa las reglas del formulario: "#" subtítulo, "-" lista,
"1." lista numerada, línea en blanco entre párrafos.
"""

from datetime import date

NOTICIAS = [
    {
        'titulo': 'Éxito de la IV versión de la Copa Milled',
        'fecha': date(2026, 9, 30),
        'autor': 'LMVE',
        'resumen': (
            'La cuarta versión del torneo reunió a 17 colegios de regiones y de la Región '
            'Metropolitana del 25 al 27 de septiembre. Andrée y Mary Graham se quedaron con '
            'el primer lugar.'
        ),
        'portada': {
            'archivo': 'core/static/core/img/eventos/copa-milled-2026-completo.webp',
            'alt': 'Afiche de la Copa Milled 2026, que se jugó el 25, 26 y 27 de septiembre',
            # Solo la mitad de arriba del afiche (logo, nombre, fechas y
            # sede): entero es vertical y no cabe en el encabezado.
            'ajustes': {'x': 0.0, 'y': 0.0, 'ancho': 1.0, 'alto': 0.5},
        },
        'cuerpo': '''\
Entre el 25 y el 27 de septiembre se jugó la cuarta versión de la Copa Milled, organizada por la LMVE. Los partidos se repartieron entre British Royal School, Liceo Manuel de Salas, Thomas Morus, Instituto Alonso de Ercilla y Andrée.

# Colegios participantes

De regiones:

- Liceo Alianza Francesa de Viña del Mar
- SSCC de Viña del Mar
- Mary Graham de Villa Alemana
- Andrés Bello de La Serena
- San Luis de Alba de Valdivia

De la Región Metropolitana:

- Alemán de Santiago
- Andrée
- British Royal School
- Pedro de Valdivia de Peñalolén
- Suizo de Santiago
- Thomas Morus
- SSCC de Talagante
- Liceo Manuel de Salas
- Liceo Nacional de Maipú
- Santa María de Lo Cañas
- Don Orione
- Instituto Alonso de Ercilla

# Un evento inolvidable

El torneo fue un éxito gracias al trabajo de todo nuestro equipo y al apoyo de las profesoras Fernanda Castellanos y Magdalena Lagos, que gestionaron los espacios en sus colegios para sacar adelante la competencia.

Queremos agradecer especialmente:

- A nuestro patrocinador oficial, Trofeos y Medallas Milled.
- A Barlosport y su marca de balones Molten.
- Al Cuerpo Arbitral de la LMVE, por su profesionalismo.
- A los estudiantes de Kinesiología de la UBO, por su apoyo en la prevención y el cuidado de los deportistas.
- Al profesor Rodrigo Andreu, de British Royal School, por su constante colaboración.

La ceremonia de premiación, a cargo de la profesora Camila Busch y el profesor Cristian Adriazola, dejó encantados a los docentes de regiones, tanto por el nivel competitivo como por la convivencia entre los equipos.

# Cuadro de honor

Damas:

1. Colegio Andrée
2. Liceo Alianza Francesa de Viña del Mar
3. Liceo Manuel de Salas
4. San Luis de Alba de Valdivia

Varones:

1. Mary Graham de Villa Alemana
2. Pedro de Valdivia
3. Don Orione
4. Santa María de Lo Cañas

Destacamos el gran nivel de juego y la deportividad que mostraron todos los jóvenes en cada jornada, y agradecemos el entusiasmo de las familias que los acompañaron desde las graderías. Felicitamos también a cada profesor representante por su compromiso y su dirección técnica.

# Nos vemos en 2027

¡Los esperamos para repetir este gran torneo en 2027, cuando la Liga cumple 40 años desarrollando el deporte escolar bajo nuestro lema: "Educar a través del Deporte"!
''',
    },
    {
        'titulo': 'Finales Sub 14: horarios del sábado 21 de noviembre',
        'fecha': date(2026, 11, 19),
        'autor': 'LMVE',
        'resumen': (
            'Las divisiones Ascenso y Honor definen a sus campeones del segundo semestre. '
            'Revisa los partidos, horarios y sedes de la jornada.'
        ),
        'portada': None,
        'cuerpo': '''\
Este sábado 21 de noviembre se juegan las finales Sub 14 del Torneo Oficial LMVE del segundo semestre 2026. En una sola mañana, las divisiones Ascenso y Honor definen a sus campeones.

# División Ascenso

Sede: Liceo Manuel de Salas

- 9:00 · Semifinal 1: COM vs LMS
- 10:00 · Semifinal 2: LAB vs MAYOR
- 11:00 · 3.er y 4.º lugar: perdedores de las semifinales
- 12:00 · Final: ganadores de las semifinales

# División Honor

Sede: Alianza Francesa

- 9:00 · Semifinal 1: SUIZO vs SMDL
- 10:00 · Semifinal 2: LAF vs CSPN
- 11:00 · 3.er y 4.º lugar: perdedores de las semifinales
- 12:00 · Final: ganadores de las semifinales

# ¡Los esperamos!

Invitamos a familias, compañeros y profesores a acompañar a los equipos desde las graderías. Después de la jornada publicaremos los resultados y el cuadro de honor.
''',
    },
]
