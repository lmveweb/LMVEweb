from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from core.imagenes import derivar, imagen_social, normalizar_ajustes, procesar_foto, procesar_original
from core.models import FotoNoticia, Noticia
from core.noticias_iniciales import NOTICIAS


class Command(BaseCommand):
    help = (
        'Carga las noticias con que se estrena la sección (core/noticias_iniciales.py), '
        'publicadas y con sus fotos. Se corre una vez después de desplegar. '
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
            fotos = (1 if datos.get('portada') else 0) + len(datos.get('galeria', []))
            self.stdout.write(self.style.SUCCESS(f'Publicada, con {fotos} fotos: {datos["titulo"]}'))

    def _crear(self, datos):
        noticia = Noticia.objects.create(
            titulo=datos['titulo'], fecha=datos['fecha'], autor=datos['autor'],
            resumen=datos['resumen'], cuerpo=datos['cuerpo'], publicada=True,
        )
        # La galería primero: si no hay portada, la primera foto hace de
        # portada (igual que en el panel).
        for orden, foto in enumerate(datos.get('galeria', []), start=1):
            with open(settings.BASE_DIR / foto['archivo'], 'rb') as archivo:
                procesada = procesar_foto(archivo)
            nueva = FotoNoticia(noticia=noticia, alt=foto['alt'], orden=orden)
            nueva.cargar(procesada)
            nueva.save()

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
