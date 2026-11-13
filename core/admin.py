from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.utils.decorators import method_decorator
from django_otp.admin import OTPAdminSite
from django_ratelimit.decorators import ratelimit

from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .imagenes import FotoInvalida, imagen_social, procesar_foto
from .ip import clave_ratelimit
from .models import FotoNoticia, MensajePatrocinio, Noticia


class LmveAdminSite(OTPAdminSite):
    """Sitio de administración con 2FA obligatorio: OTPAdminSite exige,
    además de usuario/clave, que el login quede verificado por un
    dispositivo OTP confirmado (ver el comando de gestión
    habilitar_2fa). Sin un dispositivo confirmado para el usuario, el
    login por más correcto que sea no alcanza a entrar.

    Es un sitio aparte del admin.site por defecto de Django (no un
    parche sobre ese) porque así lo pide django-otp: hay que
    re-registrar los modelos acá, incluidos User y Group, que
    normalmente Django registra solo en el sitio por defecto.

    Rate limiting en el login: por IP, no por usuario, porque antes
    del 2FA no sabemos si la contraseña es correcta — lo que hay que
    frenar es a quien está probando contraseñas o códigos seguidos,
    no distinguir cuentas. La IP es la del visitante, no la del proxy
    del hosting (ver core/ip.py): con la del proxy, a cualquiera le
    alcanzaría con 10 intentos por minuto para dejar fuera a quien
    administra el sitio.
    """

    @method_decorator(ratelimit(key=clave_ratelimit, rate='10/m', method='POST'))
    def login(self, request, extra_context=None):
        return super().login(request, extra_context)


site = LmveAdminSite(LmveAdminSite.name)

site.register(User, UserAdmin)
site.register(Group, GroupAdmin)


@admin.register(MensajePatrocinio, site=site)
class MensajePatrocinioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'institucion', 'email', 'creado')
    list_filter = ('creado',)
    search_fields = ('nombre', 'institucion', 'email')
    readonly_fields = ('creado',)


# ---------------------------------------------------------------------
# Noticias
# ---------------------------------------------------------------------

FOTOS_POR_NOTICIA = 8


class FotoNoticiaForm(forms.ModelForm):
    """Recibe el archivo de la foto y lo pasa por core.imagenes antes de
    guardar: lo que queda en la base nunca es el archivo original."""

    archivo = forms.FileField(
        label='Foto', required=False,
        widget=forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        help_text='JPG, PNG o WebP, hasta 10 MB. Para cambiar una foto ya subida, elige otra acá.',
    )

    class Meta:
        model = FotoNoticia
        fields = ['archivo', 'alt', 'es_portada', 'orden']

    def clean_archivo(self):
        archivo = self.cleaned_data.get('archivo')
        if not archivo:
            if not self.instance.pk:
                raise forms.ValidationError('Falta elegir la foto.')
            return None
        try:
            self._procesada = procesar_foto(archivo)
        except FotoInvalida as error:
            raise forms.ValidationError(str(error))
        return archivo

    def save(self, commit=True):
        foto = super().save(commit=False)
        procesada = getattr(self, '_procesada', None)
        if procesada:
            foto.cargar(procesada)
        if commit:
            foto.save()
        return foto


class FotosFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        marcadas = [
            f for f in self.forms
            if getattr(f, 'cleaned_data', None)
            and f.cleaned_data.get('es_portada') and not f.cleaned_data.get('DELETE')
        ]
        if len(marcadas) > 1:
            raise forms.ValidationError(
                'Marcaste más de una foto como portada. Deja marcada solo una.'
            )


class FotoNoticiaInline(admin.TabularInline):
    model = FotoNoticia
    form = FotoNoticiaForm
    formset = FotosFormSet
    # Agrega sobre la tabla una explicación de qué foto es la portada
    # (ver la plantilla).
    template = 'core/admin/fotos_inline.html'
    extra = 1
    max_num = FOTOS_POR_NOTICIA
    fields = ['vista', 'archivo', 'alt', 'es_portada', 'orden']
    readonly_fields = ['vista']

    @admin.display(description='Vista')
    def vista(self, foto):
        if not foto.pk:
            return '—'
        # Con atributos width/height y no con style="": la política de
        # seguridad del sitio (CSP) bloquea los estilos en línea.
        imagen = format_html(
            '<img src="{}" alt="" width="120" height="{}">',
            foto.url_miniatura, round(120 * foto.mini_alto / foto.mini_ancho),
        )
        # La marca va en la que de verdad sale de portada, esté marcada
        # o no (si no hay ninguna marcada, es la primera).
        if foto.noticia.portada.pk == foto.pk:
            return format_html('{}<span class="foto-portada-marca">Portada</span>', imagen)
        return imagen


@admin.register(Noticia, site=site)
class NoticiaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'fecha', 'publicada', 'cantidad_fotos')
    list_filter = ('publicada',)
    search_fields = ('titulo', 'resumen', 'cuerpo')
    date_hierarchy = 'fecha'
    inlines = [FotoNoticiaInline]

    class Media:
        css = {'all': ['core/css/admin-noticias.css']}
        js = ['core/js/admin-noticias.js']

    def get_fieldsets(self, request, obj=None):
        # La guía de escritura va justo sobre las casillas que explica.
        # Sale de una plantilla propia: es HTML escrito por nosotros, sin
        # nada que venga de un usuario.
        guia = mark_safe(render_to_string('core/admin/guia_noticia.html'))
        return [
            (None, {'fields': ('titulo', 'fecha', 'autor')}),
            ('Contenido', {'fields': ('resumen', 'cuerpo'), 'description': guia}),
            ('Publicación', {'fields': ('publicada',)}),
        ]
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 22, 'cols': 90})},
    }

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_fotos=models.Count('fotos'))

    @admin.display(description='Fotos', ordering='_fotos')
    def cantidad_fotos(self, noticia):
        return noticia._fotos

    def get_changeform_initial_data(self, request):
        """Una noticia nueva parte firmada por quien la está escribiendo
        (si su cuenta tiene nombre y apellido). Se puede cambiar o borrar."""
        inicial = super().get_changeform_initial_data(request)
        inicial.setdefault('autor', request.user.get_full_name())
        return inicial

    def save_related(self, request, form, formsets, change):
        """Después de guardar las fotos, rehace la imagen que se ve al
        compartir el link, a partir de la que quedó primera."""
        super().save_related(request, form, formsets, change)
        noticia = form.instance
        principal = noticia.fotos.values_list('grande', flat=True).first()
        noticia.imagen_social = imagen_social(principal) if principal else None
        noticia.save(update_fields=['imagen_social'])
