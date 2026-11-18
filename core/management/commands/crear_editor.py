from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction

from core.acceso import GRUPO_EDITORES, activar_codigo_por_correo, clave_temporal


class Command(BaseCommand):
    help = (
        'Crea la cuenta de una persona que va a publicar noticias, lista '
        'para entrar: acceso al panel, grupo "Editores" (solo Noticias), '
        'código de acceso por correo activado y una clave temporal. '
        'Ejemplo: crear_editor cgonzalez --nombre Carla --apellido González '
        '--email carla@example.com'
    )

    def add_arguments(self, parser):
        parser.add_argument('username', help='Nombre de usuario, sin espacios (ej. cgonzalez).')
        parser.add_argument('--nombre', required=True)
        parser.add_argument('--apellido', required=True)
        parser.add_argument('--email', required=True, help='Correo al que le llegarán los códigos de acceso.')

    def handle(self, username, nombre, apellido, email, **options):
        User = get_user_model()
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f'"{email}" no es un correo válido.')
        if User.objects.filter(username__iexact=username).exists():
            raise CommandError(f'Ya existe el usuario "{username}".')
        try:
            grupo = Group.objects.get(name=GRUPO_EDITORES)
        except Group.DoesNotExist:
            raise CommandError(f'No existe el grupo "{GRUPO_EDITORES}". Corre primero: python manage.py migrate')

        clave = clave_temporal()
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=clave,
                first_name=nombre, last_name=apellido, is_staff=True,
            )
            user.groups.add(grupo)
            activar_codigo_por_correo(user)

        self.stdout.write(self.style.SUCCESS(f'Cuenta creada para {nombre} {apellido}.'))
        self.stdout.write(f'  Usuario:          {username}')
        self.stdout.write(f'  Clave temporal:   {clave}')
        self.stdout.write(f'  Códigos al correo: {email}')
        self.stdout.write(
            'La clave no se vuelve a mostrar. Pásasela por teléfono o videollamada y pídele '
            'que la cambie al entrar (arriba a la derecha, "Cambiar contraseña").'
        )
