from django.contrib import admin

from .models import MensajePatrocinio


@admin.register(MensajePatrocinio)
class MensajePatrocinioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'institucion', 'email', 'creado')
    list_filter = ('creado',)
    search_fields = ('nombre', 'institucion', 'email')
    readonly_fields = ('creado',)
