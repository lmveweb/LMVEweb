from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django_otp.admin import OTPAdminSite
from django_ratelimit.decorators import ratelimit

import json

from django import forms
from django.db import models
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .acceso import activar_codigo_por_correo, dispositivo_de, ingresar
from .imagenes import (
    FotoInvalida,
    derivar,
    imagen_social,
    normalizar_ajustes,
    procesar_foto,
    procesar_original,
)
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

    # El ingreso es en dos pasos (ver core/acceso.py): contraseña y
    # después el código, que sale solo al correo. El límite cuenta los
    # dos pasos juntos, así que también frena a quien pruebe códigos.
    @method_decorator(sensitive_post_parameters('password', 'codigo'))
    @method_decorator(never_cache)
    @method_decorator(ratelimit(key=clave_ratelimit, rate='10/m', method='POST'))
    def login(self, request, extra_context=None):
        return ingresar(self, request, extra_context)


site = LmveAdminSite(LmveAdminSite.name)


class UsuarioAdmin(UserAdmin):
    """Los usuarios de siempre, más lo que le falta a una cuenta para
    poder entrar: el código de acceso por correo. Se activa desde la
    lista (Acción → "Activar el código de acceso por correo"), sin pasar
    por la consola del hosting."""

    list_display = ('username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'codigo_por_correo')
    actions = ['activar_codigo']

    @admin.display(description='Código por correo', boolean=True)
    def codigo_por_correo(self, usuario):
        return dispositivo_de(usuario) is not None

    @admin.action(description='Activar el código de acceso por correo')
    def activar_codigo(self, request, queryset):
        # Decide quién puede entrar al panel: solo quien ya lo administra.
        if not request.user.is_superuser:
            raise PermissionDenied
        for usuario in queryset:
            if not usuario.email:
                self.message_user(
                    request,
                    f'{usuario.get_username()} no tiene correo en su ficha: el código no tendría a dónde llegar.',
                    messages.ERROR,
                )
                continue
            activar_codigo_por_correo(usuario)
            self.message_user(
                request, f'{usuario.get_username()}: los códigos llegarán a {usuario.email}.', messages.SUCCESS,
            )


site.register(User, UsuarioAdmin)
site.register(Group, GroupAdmin)


@admin.register(MensajePatrocinio, site=site)
class MensajePatrocinioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'institucion', 'email', 'creado')
    list_filter = ('creado',)
    search_fields = ('nombre', 'institucion', 'email')
    readonly_fields = ('creado',)


# ---------------------------------------------------------------------
# Noticias
#
# El formulario va en tres pestañas (las arma core/static/core/js/
# admin-noticias.js; sin JavaScript se ve todo seguido):
#   Texto          título, fecha, autor, resumen y texto
#   Fotos          la foto de portada y, aparte, las de la galería
#   Editar portada recortar, girar y ajustar la portada, con vista previa
# ---------------------------------------------------------------------

FOTOS_POR_NOTICIA = 8
TIPOS_DE_FOTO = 'image/jpeg,image/png,image/webp'


class NoticiaAdminForm(forms.ModelForm):
    """Formulario de la noticia, más su foto de portada.

    La portada es una FotoNoticia con es_portada=True, pero no se maneja
    en la tabla de la galería: tiene su propia casilla para subirla, su
    descripción y los ajustes del editor (un JSON en un campo oculto que
    llena el editor). Se guarda en NoticiaAdmin.save_related.
    """

    portada_archivo = forms.FileField(
        label='Foto de portada', required=False,
        widget=forms.FileInput(attrs={'accept': TIPOS_DE_FOTO}),
        help_text='JPG, PNG o WebP, hasta 10 MB. Si ya hay una, elegir otra la reemplaza.',
    )
    portada_alt = forms.CharField(
        label='Descripción de la portada', max_length=160, required=False,
        widget=forms.TextInput(attrs={'size': 70}),
        help_text='Qué se ve en la foto, en una frase. La escuchan las personas ciegas que visitan el sitio.',
    )
    portada_quitar = forms.BooleanField(label='Quitar la foto de portada', required=False)
    portada_ajustes = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Noticia
        fields = ['titulo', 'fecha', 'autor', 'resumen', 'cuerpo', 'publicada']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portada = None
        if self.instance.pk:
            self.portada = self.instance.fotos.filter(es_portada=True).first()
        if self.portada:
            self.fields['portada_alt'].initial = self.portada.alt
            self.fields['portada_ajustes'].initial = json.dumps(normalizar_ajustes(self.portada.ajustes))
        else:
            # Sin portada todavía no hay nada que quitar.
            del self.fields['portada_quitar']

    def clean_portada_archivo(self):
        archivo = self.cleaned_data.get('portada_archivo')
        self._original = None
        if archivo:
            try:
                self._original = procesar_original(archivo)
            except FotoInvalida as error:
                raise forms.ValidationError(str(error))
        return archivo

    def clean_portada_ajustes(self):
        # Lo escribe el editor; si llega roto o adulterado, se corrige
        # (normalizar_ajustes nunca falla) en vez de molestar a quien
        # está publicando con un error que no puede entender.
        try:
            datos = json.loads(self.cleaned_data.get('portada_ajustes') or '{}')
        except ValueError:
            datos = {}
        return normalizar_ajustes(datos)

    def clean(self):
        datos = super().clean()
        quitar = datos.get('portada_quitar')
        hay_portada = getattr(self, '_original', None) or (self.portada and not quitar)
        if hay_portada and not (datos.get('portada_alt') or '').strip():
            self.add_error('portada_alt', 'Falta describir la foto de portada.')
        return datos

    def guardar_portada(self, noticia):
        datos = self.cleaned_data
        if datos.get('portada_quitar') and not self._original:
            if self.portada:
                self.portada.delete()
            return

        ajustes = datos['portada_ajustes']
        if self._original:
            original = self._original
            # Una foto nueva parte sin los recortes de la anterior, salvo
            # que se hayan editado sobre la nueva (el editor los reinicia
            # al elegir otro archivo).
            if self.portada and ajustes == normalizar_ajustes(self.portada.ajustes):
                ajustes = normalizar_ajustes({})
        elif self.portada:
            if ajustes == normalizar_ajustes(self.portada.ajustes):
                # Sin foto nueva ni cambios en el editor: solo la descripción.
                if self.portada.alt != datos['portada_alt']:
                    self.portada.alt = datos['portada_alt']
                    self.portada.save(update_fields=['alt'])
                return
            guardadas = FotoNoticia.objects.filter(pk=self.portada.pk).values_list('original', 'grande').get()
            # Una portada sin original guardado (anterior al editor) se
            # edita a partir de su versión grande.
            original = bytes(guardadas[0] or guardadas[1])
        else:
            return

        foto = self.portada or FotoNoticia(noticia=noticia, es_portada=True)
        foto.alt = datos['portada_alt']
        foto.original = original
        foto.ajustes = ajustes
        foto.cargar(derivar(original, ajustes))
        foto.save()


class FotoNoticiaForm(forms.ModelForm):
    """Una foto de la galería. Recibe el archivo y lo pasa por
    core.imagenes antes de guardar: lo que queda en la base nunca es el
    archivo original."""

    archivo = forms.FileField(
        label='Foto', required=False,
        widget=forms.FileInput(attrs={'accept': TIPOS_DE_FOTO}),
        help_text='JPG, PNG o WebP, hasta 10 MB. Para cambiar una foto ya subida, elige otra acá.',
    )

    class Meta:
        model = FotoNoticia
        fields = ['archivo', 'alt', 'orden']

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


class FotoNoticiaInline(admin.TabularInline):
    """Las fotos de la galería del final. La portada no aparece acá: se
    sube y se edita aparte (ver NoticiaAdminForm)."""

    model = FotoNoticia
    form = FotoNoticiaForm
    verbose_name = 'Foto de la galería'
    verbose_name_plural = 'Fotos de la galería'
    extra = 1
    max_num = FOTOS_POR_NOTICIA
    fields = ['foto_actual', 'archivo', 'alt', 'orden']
    readonly_fields = ['foto_actual']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(es_portada=False)

    @admin.display(description='Subida')
    def foto_actual(self, foto):
        # Un enlace y no una miniatura: con varias fotos, las miniaturas
        # alargaban demasiado el formulario.
        if not foto.pk:
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">Ver foto</a>', foto.url_grande)


@admin.register(Noticia, site=site)
class NoticiaAdmin(admin.ModelAdmin):
    form = NoticiaAdminForm
    list_display = ('titulo', 'fecha', 'publicada', 'cantidad_fotos')
    list_filter = ('publicada',)
    search_fields = ('titulo', 'resumen', 'cuerpo')
    date_hierarchy = 'fecha'
    inlines = [FotoNoticiaInline]
    formfield_overrides = {
        models.TextField: {'widget': forms.Textarea(attrs={'rows': 22, 'cols': 90})},
    }

    class Media:
        css = {'all': ['core/css/admin-noticias.css']}
        js = ['core/js/admin-noticias.js']

    def get_fieldsets(self, request, obj=None):
        # Las guías y el editor salen de plantillas propias: es HTML
        # escrito por nosotros. Lo único de la base que llega al editor
        # es la dirección de la foto, que arma reverse().
        portada = obj.fotos.filter(es_portada=True).first() if obj else None
        editor = render_to_string('core/admin/editor_portada.html', {
            'url_original': portada.url_original if portada else '',
        })
        return [
            ('Texto', {
                'classes': ('pestana', 'pestana-texto'),
                'fields': ('titulo', 'fecha', 'autor', 'resumen', 'cuerpo'),
                'description': mark_safe(render_to_string('core/admin/guia_noticia.html')),
            }),
            ('Foto de portada', {
                'classes': ('pestana', 'pestana-fotos'),
                'fields': ('portada_archivo', 'portada_alt', 'portada_quitar') if portada
                else ('portada_archivo', 'portada_alt'),
                'description': mark_safe(render_to_string('core/admin/guia_fotos.html')),
            }),
            ('Editar portada', {
                'classes': ('pestana', 'pestana-editor'),
                'fields': ('portada_ajustes',),
                'description': mark_safe(editor),
            }),
            ('Publicación', {
                'classes': ('pestana-publicacion',),
                'fields': ('publicada',),
            }),
        ]

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
        """Después de guardar la galería, guarda la portada y rehace la
        imagen que se ve al compartir el link, a partir de la que quedó
        primera (la portada, o si no hay, la primera de la galería)."""
        super().save_related(request, form, formsets, change)
        noticia = form.instance
        form.guardar_portada(noticia)
        principal = noticia.fotos.values_list('grande', flat=True).first()
        noticia.imagen_social = imagen_social(principal) if principal else None
        noticia.save(update_fields=['imagen_social'])

