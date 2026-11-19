"""Tests de las páginas de error propias (core/errores.py) y del comando
que carga las noticias de estreno."""

import time
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import path, reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_email.models import EmailDevice

from .acceso import GRUPO_EDITORES
from .models import FotoNoticia, Noticia
from .noticias_iniciales import NOTICIAS
from LMVEweb.urls import ADMIN_URL


def _explota(request):
    raise RuntimeError('error de prueba')


# Urlconf de prueba para el 500 (ver test_un_error_del_servidor_muestra_la_pagina_propia).
urlpatterns = [path('explota/', _explota)]


class PaginasDeErrorTests(TestCase):
    def _sin_indexar(self, r):
        self.assertContains(r, '<meta name="robots" content="noindex, follow">', status_code=r.status_code)
        self.assertNotContains(r, 'rel="canonical"', status_code=r.status_code)

    def test_una_direccion_que_no_existe_muestra_la_pagina_propia(self):
        r = self.client.get('/no-existe/')
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, 'Página no encontrada', status_code=404)
        self.assertContains(r, f'href="{reverse("contacto")}"', status_code=404)
        self.assertContains(r, 'class="btn-cta"', status_code=404)  # con el encabezado del sitio
        self._sin_indexar(r)

    def test_una_noticia_que_no_existe_lo_dice_y_lleva_a_las_noticias(self):
        r = self.client.get('/noticias/una-noticia-que-no-existe/')
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, 'Esa noticia no existe o ya no está publicada', status_code=404)
        self.assertContains(r, 'Ver todas las noticias', status_code=404)
        self._sin_indexar(r)

    def test_un_borrador_para_el_publico_muestra_el_mismo_mensaje(self):
        noticia = Noticia.objects.create(titulo='Borrador', resumen='R', cuerpo='C')
        r = self.client.get(noticia.get_absolute_url())
        self.assertContains(r, 'Esa noticia no existe o ya no está publicada', status_code=404)
        self.assertNotContains(r, 'Borrador', status_code=404)

    def test_un_editor_en_una_seccion_ajena_del_panel_ve_un_mensaje_del_panel(self):
        editor = User.objects.create_user('editora', password='x', is_staff=True)
        editor.groups.add(Group.objects.get(name=GRUPO_EDITORES))
        dispositivo = EmailDevice.objects.create(user=editor, name='default', confirmed=True)
        self.client.force_login(editor)
        sesion = self.client.session
        sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
        sesion.save()
        r = self.client.get(reverse('admin:auth_user_changelist'))
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, 'Tu cuenta no tiene permiso para ver esta sección', status_code=403)
        self.assertContains(r, f'href="{reverse("admin:index")}"', status_code=403)

    def test_demasiados_intentos_en_el_login_lo_explica(self):
        cache.clear()
        login = f'/{ADMIN_URL}login/'
        # Reloj fijo: ver test_rate_limit_en_login en core/tests.py.
        with patch('django_ratelimit.core.time.time', return_value=time.time()):
            for _ in range(10):
                self.client.post(login, {'username': 'nadie', 'password': 'mala'})
            r = self.client.post(login, {'username': 'nadie', 'password': 'mala'})
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, 'Espera un minuto', status_code=403)

    def test_un_formulario_vencido_explica_que_hay_que_recargar(self):
        cliente = Client(enforce_csrf_checks=True)
        r = cliente.post(f'/{ADMIN_URL}login/', {'username': 'x', 'password': 'y'})
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, 'La página estuvo abierta mucho tiempo', status_code=403)
        r = cliente.post(reverse('contacto'), {})
        self.assertContains(r, 'recárgala', status_code=403)
        self._sin_indexar(r)

    @override_settings(ROOT_URLCONF='core.tests_errores')
    def test_un_error_del_servidor_muestra_la_pagina_propia(self):
        self.client.raise_request_exception = False
        r = self.client.get('/explota/')
        self.assertEqual(r.status_code, 500)
        self.assertContains(r, 'Algo falló de nuestro lado', status_code=500)
        self.assertContains(r, 'core/css/error', status_code=500)
        self.assertContains(r, 'noindex', status_code=500)
        # Un comentario {# #} de varias líneas no es comentario en Django:
        # se imprime tal cual en la página.
        self.assertNotContains(r, '{#', status_code=500)
        self.assertNotContains(r, 'nonce', status_code=500)

    def test_ninguna_plantilla_tiene_comentarios_de_varias_lineas(self):
        from pathlib import Path
        for plantilla in Path(__file__).parent.joinpath('templates').rglob('*.html'):
            for n, linea in enumerate(plantilla.read_text(encoding='utf-8').splitlines(), 1):
                if '{#' in linea:
                    self.assertIn('#}', linea, f'{plantilla.name}:{n}: un {{# #}} de varias líneas se imprime; usar {{% comment %}}')

    def test_las_vistas_previas_no_existen_en_produccion(self):
        # Los tests corren con DEBUG=False, igual que producción.
        self.assertEqual(self.client.get('/vista-previa-error/500/').status_code, 404)


class CargarNoticiasInicialesTests(TestCase):
    def _cargar(self):
        salida = StringIO()
        call_command('cargar_noticias_iniciales', stdout=salida)
        return salida.getvalue()

    def test_carga_las_noticias_publicadas_y_con_su_portada(self):
        self._cargar()
        self.assertEqual(Noticia.objects.filter(publicada=True).count(), len(NOTICIAS))
        copa = Noticia.objects.get(titulo__contains='Copa Milled')
        portada = copa.fotos.get(es_portada=True)
        self.assertTrue(portada.alt)
        self.assertTrue(Noticia.objects.filter(pk=copa.pk, imagen_social__isnull=False).exists())
        r = self.client.get(copa.get_absolute_url())
        self.assertContains(r, '<h2>Cuadro de honor</h2>')
        self.assertContains(r, '<li>Colegio Andrée</li>')
        self.assertEqual(self.client.get(portada.url_grande).status_code, 200)

    def test_las_noticias_salen_en_la_lista_y_en_la_portada(self):
        self._cargar()
        for url in (reverse('noticias'), reverse('home')):
            html = self.client.get(url).content.decode()
            for datos in NOTICIAS:
                self.assertIn(datos['titulo'], html)

    def test_cada_noticia_trae_su_portada_y_su_galeria_sin_metadatos(self):
        import io
        from PIL import Image
        self._cargar()
        for datos in NOTICIAS:
            noticia = Noticia.objects.get(titulo=datos['titulo'])
            self.assertEqual(noticia.fotos.filter(es_portada=True).count(), 1 if datos.get('portada') else 0)
            self.assertEqual(noticia.fotos.filter(es_portada=False).count(), len(datos.get('galeria', [])))
            for foto in FotoNoticia.objects.filter(noticia=noticia).values('alt', 'grande'):
                self.assertTrue(foto['alt'])
                self.assertFalse(dict(Image.open(io.BytesIO(bytes(foto['grande']))).getexif()))
            html = self.client.get(noticia.get_absolute_url()).content.decode()
            if datos.get('galeria'):
                self.assertIn('class="noticia-galeria"', html)

    def test_las_fotos_de_origen_no_traen_metadatos(self):
        from pathlib import Path
        from PIL import Image
        from django.conf import settings
        for datos in NOTICIAS:
            for foto in [datos.get('portada')] + datos.get('galeria', []):
                if foto and 'fotos_iniciales' in foto['archivo']:
                    with Image.open(Path(settings.BASE_DIR) / foto['archivo']) as imagen:
                        self.assertFalse(dict(imagen.getexif()), foto['archivo'])
                        self.assertNotIn('xmp', imagen.info, foto['archivo'])

    def test_correrlo_de_nuevo_no_duplica_ni_pisa_lo_editado(self):
        self._cargar()
        Noticia.objects.filter(titulo=NOTICIAS[0]['titulo']).update(resumen='Editado desde el panel')
        salida = self._cargar()
        self.assertIn('Ya existe', salida)
        self.assertEqual(Noticia.objects.count(), len(NOTICIAS))
        fotos = sum((1 if d.get('portada') else 0) + len(d.get('galeria', [])) for d in NOTICIAS)
        self.assertEqual(FotoNoticia.objects.count(), fotos)
        self.assertEqual(Noticia.objects.get(titulo=NOTICIAS[0]['titulo']).resumen, 'Editado desde el panel')
