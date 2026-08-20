from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='mensajepatrocinio',
            old_name='contacto',
            new_name='nombre',
        ),
        migrations.RenameField(
            model_name='mensajepatrocinio',
            old_name='empresa',
            new_name='institucion',
        ),
        migrations.RemoveField(
            model_name='mensajepatrocinio',
            name='interes',
        ),
        migrations.AlterField(
            model_name='mensajepatrocinio',
            name='nombre',
            field=models.CharField(max_length=200, verbose_name='Nombre y Apellido'),
        ),
        migrations.AlterField(
            model_name='mensajepatrocinio',
            name='institucion',
            field=models.CharField(blank=True, max_length=200, verbose_name='Institución'),
        ),
        migrations.AlterField(
            model_name='mensajepatrocinio',
            name='mensaje',
            field=models.TextField(verbose_name='Mensaje'),
        ),
    ]
