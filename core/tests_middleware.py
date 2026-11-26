"""Dirección única del sitio y tope de subida (core/middleware.py)."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from LMVEweb.urls import ADMIN_URL

LOGIN_URL = f'/{ADMIN_URL}login/'


@override_settings(SITE_URL='https://ligamve.cl', ALLOWED_HOSTS=['ligamve.cl', 'lmveweb.onrender.com'])
class DominioDeRenderTests(TestCase):
    def test_la_direccion_de_render_redirige_al_dominio_propio(self):
        r = self.client.get('/noticias/?pagina=2', HTTP_HOST='lmveweb.onrender.com')
        self.assertEqual(r.status_code, 301)
        self.assertEqual(r['Location'], 'https://ligamve.cl/noticias/?pagina=2')

    def test_tambien_redirige_un_post(self):
        r = self.client.post('/contacto/', {}, HTTP_HOST='lmveweb.onrender.com')
        self.assertEqual(r.status_code, 301)

    def test_el_dominio_propio_no_se_redirige(self):
        self.assertEqual(self.client.get('/', HTTP_HOST='ligamve.cl').status_code, 200)


class TopeDeSubidaTests(TestCase):
    MB = 1024 * 1024

    def _post(self, url, megas):
        # Basta con declarar el tamaño: el tope se revisa antes de leer
        # el cuerpo, que es justamente lo que evita recibirlo entero.
        return self.client.generic('POST', url, b'x', CONTENT_TYPE='application/octet-stream',
                                   CONTENT_LENGTH=str(int(megas * self.MB)))

    def test_sin_sesion_no_se_acepta_un_envio_grande(self):
        for url in (reverse('contacto'), LOGIN_URL):
            with self.subTest(url=url):
                self.assertEqual(self._post(url, 2).status_code, 413)

    def test_sin_sesion_un_envio_normal_pasa(self):
        # Un mensaje de Contacto pesa unos pocos KB.
        self.assertNotEqual(self._post(reverse('contacto'), 0.5).status_code, 413)

    def test_el_equipo_del_panel_puede_subir_todas_las_fotos_de_una_noticia(self):
        # Portada + 8 fotos de galería, de hasta 10 MB cada una.
        editor = User.objects.create_user('editor', password='x', is_staff=True)
        self.client.force_login(editor)
        url = f'/{ADMIN_URL}core/noticia/add/'
        self.assertNotEqual(self._post(url, 90).status_code, 413)
        self.assertEqual(self._post(url, 120).status_code, 413)
