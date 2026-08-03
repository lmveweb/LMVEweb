from django.db import models


class MensajePatrocinio(models.Model):
    """Una fila = un envío del formulario de Contacto."""

    class NivelInteres(models.TextChoices):
        NAMING = 'naming', 'Main Sponsor (Naming Rights)'
        APPAREL = 'apparel', 'Indumentaria y Equipamiento'
        DIGITAL = 'digital', 'Digital & Streaming Partner'
        OTHER = 'other', 'Activaciones y BTL en recinto'

    empresa = models.CharField('Empresa o Marca', max_length=200)
    contacto = models.CharField('Persona de Contacto', max_length=200)
    email = models.EmailField('Correo Electrónico')
    interes = models.CharField(
        'Nivel de Interés', max_length=20, choices=NivelInteres.choices
    )
    mensaje = models.TextField('Mensaje Adicional', blank=True)
    creado = models.DateTimeField('Fecha de Envío', auto_now_add=True)

    class Meta:
        verbose_name = 'Mensaje de Patrocinio'
        verbose_name_plural = 'Mensajes de Patrocinio'
        ordering = ['-creado']

    def __str__(self):
        return f'{self.empresa} ({self.creado:%Y-%m-%d %H:%M})'
