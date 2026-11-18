from django.db import migrations

# Quien publica las noticias de la Liga: todo sobre Noticias y sus
# fotos (crear, editar, borrar) y nada más. No ve los mensajes de
# Contacto ni las cuentas del panel.
GRUPO = 'Editores'
MODELOS = {'noticia': 'Noticia', 'fotonoticia': 'Foto'}
ACCIONES = ['add', 'change', 'delete', 'view']


def crear_grupo(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    grupo, _ = Group.objects.get_or_create(name=GRUPO)
    permisos = []
    for modelo, nombre in MODELOS.items():
        # Django crea los permisos al TERMINAR de migrar (post_migrate),
        # así que en una base nueva todavía no existen acá. Se crean
        # iguales a los que haría Django, que después los encuentra y no
        # los duplica.
        tipo, _ = ContentType.objects.get_or_create(app_label='core', model=modelo)
        for accion in ACCIONES:
            permiso, _ = Permission.objects.get_or_create(
                content_type=tipo, codename=f'{accion}_{modelo}',
                defaults={'name': f'Can {accion} {nombre}'},
            )
            permisos.append(permiso)
    grupo.permissions.set(permisos)


def borrar_grupo(apps, schema_editor):
    apps.get_model('auth', 'Group').objects.filter(name=GRUPO).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_portada_editable'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.RunPython(crear_grupo, borrar_grupo),
    ]
