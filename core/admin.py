from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.utils.decorators import method_decorator
from django_otp.admin import OTPAdminSite
from django_ratelimit.decorators import ratelimit

from .models import MensajePatrocinio


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
    no distinguir cuentas.
    """

    @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'))
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
