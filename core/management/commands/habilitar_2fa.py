from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_email.models import EmailDevice


class Command(BaseCommand):
    help = (
        'Habilita el 2FA por correo para un usuario del admin: crea (o '
        'reemplaza) su dispositivo OTP y lo deja confirmado directamente, '
        'sin el paso intermedio de "ingresa el código que te mandamos para '
        'confirmar el dispositivo" que trae django-otp de fábrica — un '
        'flujo pensado para que el usuario mismo se autoconfirme desde una '
        'vista, que acá no armamos porque son uno o dos admins nomás.'
    )

    def add_arguments(self, parser):
        parser.add_argument('username')
        parser.add_argument(
            '--email',
            default=None,
            help=(
                'Correo al que van a llegar los códigos. Sin esto, usa el '
                'campo email del usuario.'
            ),
        )

    def handle(self, username, email, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'No existe el usuario "{username}".')

        destino = email or user.email
        if not destino:
            raise CommandError(
                f'"{username}" no tiene un email guardado y no se pasó --email. '
                'El código de acceso no tendría a dónde llegar.'
            )

        device, creado = EmailDevice.objects.update_or_create(
            user=user,
            name='default',
            defaults={'email': email or '', 'confirmed': True},
        )
        verbo = 'creado' if creado else 'actualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Dispositivo 2FA {verbo} para "{username}". '
            f'Los códigos de acceso van a llegar a: {destino}'
        ))
