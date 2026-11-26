"""Origen de las visitas y tope de subida (core/middleware.py y core/ip.py).

Producción está detrás de Cloudflare, que entrega la IP real del
visitante en CF-Connecting-IP. Pero a Render se puede llegar directo,
sin pasar por Cloudflare, y ahí ese encabezado lo escribe quien quiera:
con una IP inventada en cada intento, el límite del login no frena a
nadie. Cloudflare agrega una clave secreta a cada visita (una regla de
"Transform Rules"), y solo cuando viene esa clave se confía en la IP.
"""

from unittest.mock import patch

import time

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .ip import ip_cliente
from .middleware import ENCABEZADO_ORIGEN, OrigenDelProxyMiddleware
from LMVEweb.urls import ADMIN_URL

LOGIN_URL = f'/{ADMIN_URL}login/'
CLAVE = 'clave-de-prueba-larga-y-secreta'
PROXY = '10.0.0.1'
META_ORIGEN = 'HTTP_' + ENCABEZADO_ORIGEN.upper().replace('-', '_')


def _request_procesado(**meta):
    """Un request que ya pasó por el middleware, como lo ve una vista."""
    request = RequestFactory().get('/', REMOTE_ADDR=PROXY, **meta)
    OrigenDelProxyMiddleware(lambda r: None)(request)
    return request


@override_settings(IP_CLIENTE_ENCABEZADO='CF-Connecting-IP', PROXY_CLAVE=CLAVE)
class ClaveDelProxyTests(TestCase):
    def test_con_la_clave_correcta_se_usa_la_ip_que_entrega_cloudflare(self):
        request = _request_procesado(HTTP_CF_CONNECTING_IP='198.51.100.9', **{META_ORIGEN: CLAVE})
        self.assertEqual(ip_cliente(request), '198.51.100.9')

    def test_sin_la_clave_o_con_otra_no_se_confia_en_el_encabezado(self):
        for clave in (None, '', 'otra-clave', CLAVE + 'x'):
            with self.subTest(clave=clave):
                meta = {'HTTP_CF_CONNECTING_IP': '198.51.100.9'}
                if clave is not None:
                    meta[META_ORIGEN] = clave
                self.assertEqual(ip_cliente(_request_procesado(**meta)), PROXY)

    def test_la_clave_se_borra_del_request_para_no_filtrarse(self):
        # Sentry adjunta los encabezados del request a cada error: la
        # clave no puede seguir ahí una vez revisada.
        request = _request_procesado(HTTP_CF_CONNECTING_IP='198.51.100.9', **{META_ORIGEN: CLAVE})
        self.assertNotIn(META_ORIGEN, request.META)
        self.assertNotIn(CLAVE, str(request.META))

    def test_espacios_alrededor_de_la_clave_no_la_invalidan(self):
        request = _request_procesado(HTTP_CF_CONNECTING_IP='198.51.100.9', **{META_ORIGEN: f' {CLAVE} '})
        self.assertEqual(ip_cliente(request), '198.51.100.9')

    def test_el_estado_dice_que_paso_con_la_clave_sin_mostrarla(self):
        casos = {
            CLAVE: 'clave verificada',
            None: 'no llegó la clave',
            'otra': f'clave distinta (4 caracteres; se esperaban {len(CLAVE)})',
        }
        for recibida, esperado in casos.items():
            with self.subTest(recibida=recibida):
                meta = {} if recibida is None else {META_ORIGEN: recibida}
                estado = _request_procesado(**meta).origen_estado
                self.assertEqual(estado, esperado)
                self.assertNotIn(CLAVE, estado)

    def test_sin_pasar_por_el_middleware_no_se_confia(self):
        request = RequestFactory().get('/', REMOTE_ADDR=PROXY, HTTP_CF_CONNECTING_IP='198.51.100.9',
                                       **{META_ORIGEN: CLAVE})
        self.assertEqual(ip_cliente(request), PROXY)

    def test_el_login_no_se_salta_inventando_ips_sin_la_clave(self):
        cache.clear()
        reloj = patch('django_ratelimit.core.time.time', return_value=time.time())
        reloj.start()
        self.addCleanup(reloj.stop)

        def intento(ip, **meta):
            return self.client.post(LOGIN_URL, {'username': 'nadie', 'password': 'mala'},
                                    REMOTE_ADDR=PROXY, HTTP_CF_CONNECTING_IP=ip, **meta).status_code

        for i in range(10):
            self.assertEqual(intento(f'198.51.100.{i}'), 200)
        self.assertEqual(intento('198.51.100.99'), 403)
        # Quien entra por Cloudflare (con la clave) tiene su propio cupo.
        self.assertEqual(intento('198.51.100.100', **{META_ORIGEN: CLAVE}), 200)


class SinClaveConfiguradaTests(TestCase):
    @override_settings(IP_CLIENTE_ENCABEZADO='CF-Connecting-IP', PROXY_CLAVE='')
    def test_sin_clave_configurada_se_comporta_como_antes(self):
        # Permite desplegar el código antes de crear la regla en
        # Cloudflare sin que cambie nada.
        request = _request_procesado(HTTP_CF_CONNECTING_IP='198.51.100.9')
        self.assertEqual(ip_cliente(request), '198.51.100.9')


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
