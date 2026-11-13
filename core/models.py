import hashlib

from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class MensajePatrocinio(models.Model):
    """Una fila = un envío del formulario de Contacto."""

    nombre = models.CharField('Nombre y Apellido', max_length=200)
    institucion = models.CharField('Institución', max_length=200, blank=True)
    email = models.EmailField('Correo Electrónico')
    mensaje = models.TextField('Mensaje')
    creado = models.DateTimeField('Fecha de Envío', auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de Patrocinio'
        verbose_name_plural = 'Mensajes de Patrocinio'
        ordering = ['-creado']

    def __str__(self):
        return f'{self.nombre} ({self.creado:%Y-%m-%d %H:%M})'


# ---------------------------------------------------------------------
# Noticias
#
# A diferencia del resto del contenido del sitio (core/contenido.py), las
# noticias viven en la base de datos: las publica la gente de la Liga
# desde el admin, sin tocar código ni depender de quien mantiene el sitio.
# ---------------------------------------------------------------------

class _SinBinarios(models.Manager):
    """Las fotos se guardan dentro de la base (ver FotoNoticia). Este
    manager deja esas columnas fuera de las consultas normales: listar
    diez noticias no puede traerse varios MB de fotos que nadie pidió.
    Se leen solo en las vistas que sirven la imagen."""

    binarios = ()

    def get_queryset(self):
        return super().get_queryset().defer(*self.binarios)


class _NoticiaManager(_SinBinarios):
    binarios = ('imagen_social',)

    def publicadas(self):
        return self.get_queryset().filter(publicada=True)


class Noticia(models.Model):
    titulo = models.CharField('Título', max_length=120)
    # No se edita a mano: se arma una vez desde el título (ver save) y
    # no cambia más, para que un link ya compartido siga funcionando
    # aunque después se corrija el título.
    slug = models.SlugField(max_length=140, unique=True, editable=False)
    fecha = models.DateField(
        'Fecha', default=timezone.localdate,
        help_text='La fecha que se muestra en la noticia. Las más nuevas salen primero.',
    )
    resumen = models.CharField(
        'Resumen', max_length=200,
        help_text='Una o dos frases. Es lo que se lee en la tarjeta de la noticia.',
    )
    cuerpo = models.TextField(
        'Texto de la noticia', validators=[MaxLengthValidator(20000)],
        help_text=(
            'Escribe el texto tal cual, sin formato. '
            'Deja una línea en blanco entre un párrafo y el siguiente. '
            'Para una lista, empieza cada línea con un guion (- ) o con un número (1. ). '
            'Para un subtítulo, empieza la línea con # (por ejemplo: # Cuadro de Honor).'
        ),
    )
    publicada = models.BooleanField(
        'Publicada', default=False,
        help_text='Sin marcar, la noticia queda como borrador: solo se ve entrando desde este panel.',
    )
    # JPEG de 1200×630 para la vista previa al compartir el link. Se
    # regenera sola desde la primera foto cada vez que se guarda.
    imagen_social = models.BinaryField(null=True, editable=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = _NoticiaManager()

    class Meta:
        verbose_name = 'Noticia'
        verbose_name_plural = 'Noticias'
        ordering = ['-fecha', '-id']

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._slug_libre()
        super().save(*args, **kwargs)

    def _slug_libre(self):
        base = slugify(self.titulo)[:120].strip('-') or 'noticia'
        slug, n = base, 2
        while Noticia.objects.filter(slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        return slug

    def get_absolute_url(self):
        return reverse('noticia', args=[self.slug])

    @property
    def portada(self):
        """La primera foto, o None. Usa las fotos ya traídas con
        prefetch_related('fotos') cuando las hay."""
        fotos = list(self.fotos.all())
        return fotos[0] if fotos else None


class _FotoManager(_SinBinarios):
    binarios = ('miniatura', 'grande')


class FotoNoticia(models.Model):
    """Una foto de una noticia, guardada dentro de la base de datos.

    En la base y no como archivo porque el disco del hosting se borra en
    cada despliegue: un archivo subido desde el admin desaparecería con
    el próximo cambio al sitio. Así, además, las fotos entran en el
    mismo respaldo que el resto de los datos y no hace falta contratar
    ni cuidar un servicio de almacenamiento aparte. Son pocas y livianas
    (unos 250 KB por foto entre sus dos tamaños, ver core/imagenes.py).
    """

    noticia = models.ForeignKey(Noticia, on_delete=models.CASCADE, related_name='fotos')
    orden = models.PositiveSmallIntegerField(
        'Orden', default=0,
        help_text='La de número más bajo es la foto principal.',
    )
    alt = models.CharField(
        'Descripción', max_length=160,
        help_text='Qué se ve en la foto, en una frase. La escuchan las personas ciegas que visitan el sitio.',
    )
    miniatura = models.BinaryField(editable=False)
    grande = models.BinaryField(editable=False)
    ancho = models.PositiveSmallIntegerField(editable=False)
    alto = models.PositiveSmallIntegerField(editable=False)
    mini_ancho = models.PositiveSmallIntegerField(editable=False)
    mini_alto = models.PositiveSmallIntegerField(editable=False)
    # Cambia cuando cambia la imagen y va en su dirección: así el
    # navegador puede guardarla "para siempre" sin mostrar nunca una
    # versión vieja.
    version = models.CharField(max_length=12, editable=False)

    objects = _FotoManager()

    class Meta:
        verbose_name = 'Foto'
        verbose_name_plural = 'Fotos'
        ordering = ['orden', 'id']

    def __str__(self):
        return self.alt or f'Foto {self.pk}'

    def cargar(self, procesada):
        """Asigna el resultado de core.imagenes.procesar_foto."""
        for campo, valor in procesada.items():
            setattr(self, campo, valor)
        self.version = hashlib.sha256(procesada['grande']).hexdigest()[:12]

    def _url(self, tamano):
        return reverse('noticia_foto', args=[self.pk, self.version, tamano])

    @property
    def url_miniatura(self):
        return self._url('m')

    @property
    def url_grande(self):
        return self._url('g')
