from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.imagenes import derivar, imagen_social, normalizar_ajustes, procesar_original
from core.models import FotoNoticia, Noticia
from core.noticias_iniciales import NOTICIAS


class Command(BaseCommand):
    help = (
        'Carga las noticias con que se estrena la sección (core/noticias_iniciales.py), '
        'publicadas y con su foto de portada. Se corre una vez después de desplegar. '
        'Si una ya existe (mismo título), no la toca: correrlo de nuevo no duplica nada '
        'ni pisa lo que se haya editado desde el panel.'
    )

    def handle(self, **options):
        for datos in NOTICIAS:
            if Noticia.objects.filter(titulo=datos['titulo']).exists():
                self.stdout.write(f'Ya existe, no se toca: {datos["titulo"]}')
                continue
            with transaction.atomic():
                self._crear(datos)
            self.stdout.write(self.style.SUCCESS(f'Publicada: {datos["titulo"]}'))

    def _crear(self, datos):
        noticia = Noticia.objects.create(
            titulo=datos['titulo'], fecha=datos['fecha'], autor=datos['autor'],
            resumen=datos['resumen'], cuerpo=datos['cuerpo'], publicada=True,
        )
        portada = datos.get('portada')
        if not portada:
            return
        # Mismo camino que una portada subida desde el panel (ver
        # NoticiaAdminForm.guardar_portada): original editable, ajustes y
        # versiones publicables.
        with open(settings.BASE_DIR / portada['archivo'], 'rb') as archivo:
            original = procesar_original(archivo)
        ajustes = normalizar_ajustes(portada.get('ajustes', {}))
        foto = FotoNoticia(noticia=noticia, es_portada=True, alt=portada['alt'],
                           original=original, ajustes=ajustes)
        foto.cargar(derivar(original, ajustes))
        foto.save()
        noticia.imagen_social = imagen_social(foto.grande)
        noticia.save(update_fields=['imagen_social'])
