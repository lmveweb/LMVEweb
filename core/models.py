from django.db import models


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
