from django.contrib import admin

from .models import MensajePatrocinio


@admin.register(MensajePatrocinio)
class MensajePatrocinioAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'contacto', 'email', 'interes', 'creado')
    list_filter = ('interes', 'creado')
    search_fields = ('empresa', 'contacto', 'email')
    readonly_fields = ('creado',)
