import json
import re
import time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.signing import Signer
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse
from django_otp.plugins.otp_email.models import EmailDevice

from .antispam import SALT_MARCA_TIEMPO, SEGUNDOS_MINIMOS
from .models import MensajePatrocinio
from LMVEweb.urls import ADMIN_URL

# Las 7 vistas públicas, tal como deben aparecer en el sitemap y llevar
# meta de SEO. Ni /staff/ (redirect) ni el admin.
VISTAS_PUBLICAS = ['home', 'proyecto', 'sobre', 'equipo', 'archivo', 'contacto', 'privacidad']


def marca_tiempo_hace(segundos):
    """Fabrica un token de marca_tiempo como si el formulario se hubiera
    cargado hace esa cantidad de segundos, sin depender de un sleep()
    real en el test. Mismo mecanismo que core.antispam.generar_marca_tiempo."""
    return Signer(salt=SALT_MARCA_TIEMPO).sign_object(time.time() - segundos)


def datos_validos(**overrides):
    datos = {
        'nombre': 'Juana Pérez',
        'institucion': 'Colegio Acme',
        'email': 'juana@acme.cl',
        'mensaje': 'Nos interesa auspiciar la temporada 2026.',
        'acepta_politica': 'on',
        # Simula un llenado humano normal: el formulario lleva un rato
        # abierto, no se toca el honeypot (se omite del todo, igual que
        # haría un navegador real con un campo vacío que un bot sí rellena).
        'marca_tiempo': marca_tiempo_hace(SEGUNDOS_MINIMOS + 5),
    }
    datos.update(overrides)
    return datos


class ContactoTests(TestCase):
    def setUp(self):
        # El rate limiting (Tanda 6) usa la misma cache entre tests; sin
        # esto, un test podría heredar los intentos consumidos por otro.
        cache.clear()

    def test_falta_campo_obligatorio(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(nombre=''))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_email_invalido(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(email='no-es-un-correo'))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_falta_mensaje(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(mensaje=''))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_campo_excede_el_maximo_de_caracteres(self):
        nombre_muy_largo = 'A' * 201  # el modelo permite hasta 200
        respuesta = self.client.post(reverse('contacto'), datos_validos(nombre=nombre_muy_largo))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_falta_aceptar_politica(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(acepta_politica=''))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_institucion_es_opcional(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(institucion=''))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 1)

    @override_settings(CONTACTO_DESTINATARIO='')
    def test_envio_exitoso(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])

        self.assertEqual(MensajePatrocinio.objects.count(), 1)
        mensaje = MensajePatrocinio.objects.get()
        self.assertEqual(mensaje.nombre, 'Juana Pérez')
        self.assertEqual(mensaje.institucion, 'Colegio Acme')
        self.assertEqual(mensaje.email, 'juana@acme.cl')

        # Sin CONTACTO_DESTINATARIO configurado, no se intenta mandar
        # correo (y el guardado del mensaje no depende de que el envío
        # funcione). Se fuerza explícito con override_settings en vez de
        # confiar en que el .env local no lo tenga configurado.
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(CONTACTO_DESTINATARIO='destino@lmve.cl')
    def test_envio_exitoso_manda_correo_de_aviso(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])

        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['destino@lmve.cl'])
        self.assertIn('Juana Pérez', correo.subject)
        self.assertIn('Colegio Acme', correo.body)


class AntiSpamTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_honeypot_relleno_finge_exito_sin_guardar(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(telefono_contacto='555-1234'))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])
        # Al bot se le finge éxito (ver core/antispam.py), pero no se
        # guarda ni se manda correo: es el mismo motivo por el que un
        # error sería contraproducente acá.
        self.assertEqual(MensajePatrocinio.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_envio_demasiado_rapido_finge_exito_sin_guardar(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(marca_tiempo=marca_tiempo_hace(0)))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_marca_tiempo_vencida_pide_recargar(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(marca_tiempo=marca_tiempo_hace(4000)))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertIn('expiró', respuesta.json()['errores'][0])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_marca_tiempo_faltante_pide_recargar(self):
        # Un POST directo sin pasar por el formulario (o un bot que ni
        # siquiera copia los campos ocultos) no trae marca_tiempo.
        respuesta = self.client.post(reverse('contacto'), datos_validos(marca_tiempo=''))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    @override_settings(TURNSTILE_SECRET_KEY='')
    def test_sin_turnstile_configurado_no_se_exige_token(self):
        # Es el estado real de hoy en local (y en producción hasta que se
        # active Turnstile): la capa simplemente no corre.
        respuesta = self.client.post(reverse('contacto'), datos_validos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])

    @override_settings(TURNSTILE_SECRET_KEY='clave-secreta-de-prueba')
    def test_turnstile_configurado_rechaza_sin_token(self):
        with patch('core.views.verificar_turnstile', return_value=False) as mock_verificar:
            respuesta = self.client.post(reverse('contacto'), datos_validos())
        mock_verificar.assert_called_once()
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    @override_settings(TURNSTILE_SECRET_KEY='clave-secreta-de-prueba')
    def test_turnstile_configurado_acepta_con_token_valido(self):
        with patch('core.views.verificar_turnstile', return_value=True) as mock_verificar:
            respuesta = self.client.post(
                reverse('contacto'),
                datos_validos(**{'cf-turnstile-response': 'token-de-prueba'}),
            )
        mock_verificar.assert_called_once_with('token-de-prueba', '127.0.0.1', 'clave-secreta-de-prueba')
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 1)


class RutasTests(TestCase):
    def test_equipo_disponible(self):
        self.assertEqual(self.client.get(reverse('equipo')).status_code, 200)

    def test_privacidad_disponible(self):
        self.assertEqual(self.client.get(reverse('privacidad')).status_code, 200)

    def test_impacto_ya_no_existe(self):
        with self.assertRaises(NoReverseMatch):
            reverse('impacto')


@override_settings(SITE_URL='https://ligamve.cl')
class SeoTests(TestCase):
    def test_robots(self):
        r = self.client.get('/robots.txt')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r['Content-Type'].startswith('text/plain'))
        self.assertContains(r, 'Sitemap: https://ligamve.cl/sitemap.xml')

    def test_sitemap_lista_las_publicas_con_dominio_canonico(self):
        r = self.client.get('/sitemap.xml')
        self.assertEqual(r.status_code, 200)
        for nombre in VISTAS_PUBLICAS:
            self.assertContains(r, f'<loc>https://ligamve.cl{reverse(nombre)}</loc>')

    def test_sitemap_no_lista_staff_ni_admin(self):
        r = self.client.get('/sitemap.xml').content.decode()
        self.assertNotIn('/staff/', r)
        self.assertNotIn('/panel-lmve/', r)

    def test_cada_vista_publica_tiene_title_description_y_canonical(self):
        for nombre in VISTAS_PUBLICAS:
            with self.subTest(vista=nombre):
                r = self.client.get(reverse(nombre))
                self.assertContains(r, '<meta name="description"')
                self.assertContains(
                    r, f'<link rel="canonical" href="https://ligamve.cl{reverse(nombre)}">')
                self.assertContains(r, 'property="og:image" content="https://ligamve.cl/')
                self.assertContains(r, '<meta name="twitter:card" content="summary_large_image">')

    def test_titles_son_unicos(self):
        titles = []
        for nombre in VISTAS_PUBLICAS:
            r = self.client.get(reverse(nombre))
            m = re.search(r'<title>(.*?)</title>', r.content.decode())
            titles.append(m.group(1))
        self.assertEqual(len(titles), len(set(titles)), f'titles repetidos: {titles}')

    def test_jsonld_de_la_home_parsea_y_declara_la_sigla(self):
        r = self.client.get(reverse('home'))
        bloque = re.search(
            r'<script type="application/ld\+json"[^>]*>(.*?)</script>', r.content.decode(), re.S)
        self.assertIsNotNone(bloque)
        datos = json.loads(bloque.group(1))
        nodos = {n['@type']: n for n in datos['@graph']}
        self.assertIn('WebSite', nodos)
        self.assertIn('LMVE', nodos['WebSite']['alternateName'])
        self.assertIn('SportsOrganization', nodos)
        self.assertEqual(nodos['SportsOrganization']['alternateName'], 'LMVE')

    def test_otras_vistas_no_llevan_jsonld(self):
        r = self.client.get(reverse('proyecto'))
        self.assertNotContains(r, 'application/ld+json')


LOGIN_URL = f'/{ADMIN_URL}login/'
CLAVE_DE_PRUEBA = 'clave-de-prueba-para-tests-9f2c'


class AdminSeguridadTests(TestCase):
    """El admin exige 2FA por correo ademas de usuario/clave (ver
    core/admin.py), y el login tiene rate limiting por IP (ver el mismo
    archivo). Estos tests ejercitan el formulario de login real, paso a
    paso, tal como lo maneja OTPAuthenticationFormMixin: 1) usuario+clave,
    2) elegir dispositivo y pedir el desafio (dispara el correo), 3)
    mandar el codigo. Sin los tres pasos no hay sesion admin, con
    cualquier usuario/clave que sea."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='admin_test', password=CLAVE_DE_PRUEBA,
            email='destino-2fa@example.com', is_staff=True, is_superuser=True,
        )

    def test_login_sin_dispositivo_2fa_nunca_entra(self):
        # Un staff con clave correcta pero SIN EmailDevice confirmado: el
        # 2FA no es opcional, asi que jamas debe quedar con sesion admin.
        r = self.client.post(LOGIN_URL, {'username': 'admin_test', 'password': CLAVE_DE_PRUEBA})
        self.assertEqual(r.status_code, 200)  # se re-muestra el form, no redirige al panel
        self.assertEqual(self.client.get(f'/{ADMIN_URL}').status_code, 302)  # sigue afuera

    def test_flujo_completo_con_codigo_correcto_entra(self):
        device = EmailDevice.objects.create(user=self.user, name='default', confirmed=True)

        # Paso 1: usuario + clave. Sin otp_token todavia, el form pide uno
        # (no es un error real, es como el form comunica "sigue, elige
        # dispositivo") y no hay sesion admin aun.
        r = self.client.post(LOGIN_URL, {'username': 'admin_test', 'password': CLAVE_DE_PRUEBA})
        self.assertEqual(r.status_code, 200)

        # Paso 2: pide el desafio (envia el codigo por correo).
        r = self.client.post(LOGIN_URL, {
            'username': 'admin_test', 'password': CLAVE_DE_PRUEBA,
            'otp_device': device.persistent_id, 'otp_challenge': '1',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ['destino-2fa@example.com'])
        self.assertIn('Admin LMVE', correo.subject)
        device.refresh_from_db()
        codigo = device.token
        self.assertTrue(codigo)
        self.assertIn(codigo, correo.body)

        # Paso 3: el codigo real. Recien aca hay sesion admin.
        r = self.client.post(LOGIN_URL, {
            'username': 'admin_test', 'password': CLAVE_DE_PRUEBA,
            'otp_device': device.persistent_id, 'otp_token': codigo,
        })
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(f'/{ADMIN_URL}').status_code, 200)

    def test_codigo_incorrecto_no_entra(self):
        device = EmailDevice.objects.create(user=self.user, name='default', confirmed=True)
        self.client.post(LOGIN_URL, {
            'username': 'admin_test', 'password': CLAVE_DE_PRUEBA,
            'otp_device': device.persistent_id, 'otp_challenge': '1',
        })
        r = self.client.post(LOGIN_URL, {
            'username': 'admin_test', 'password': CLAVE_DE_PRUEBA,
            'otp_device': device.persistent_id, 'otp_token': '000000',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get(f'/{ADMIN_URL}').status_code, 302)

    def test_rate_limit_en_login(self):
        # 10/m por IP (ver core/admin.py). Con clave mala a proposito: lo
        # que se prueba es que el rate limit frena, no el login en si.
        #
        # El reloj queda fijo (al momento real de arrancar el test, no a
        # una fecha arbitraria) durante todo el loop: is_ratelimited()
        # ubica cada intento en una ventana de 60s calculada a partir de
        # time.time(), y sin fijarlo, un test que corre justo en el borde
        # de esa ventana veria el contador reiniciarse a mitad del loop —
        # flaky de verdad, lo vimos fallar intermitente antes de este fix.
        # Tiene que ser la hora REAL (no una fecha cualquiera): el cache
        # de base de datos usa el mismo time.time() para el vencimiento de
        # TODAS sus filas, incluidas las que dejaron otros tests; congelar
        # a una fecha lejana rompe esas comparaciones.
        ahora = time.time()
        with patch('django_ratelimit.core.time.time', return_value=ahora):
            for _ in range(10):
                r = self.client.post(LOGIN_URL, {'username': 'admin_test', 'password': 'mala'})
                self.assertEqual(r.status_code, 200)
            r = self.client.post(LOGIN_URL, {'username': 'admin_test', 'password': 'mala'})
            self.assertEqual(r.status_code, 403)


class Habilitar2faCommandTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='otra_admin', password=CLAVE_DE_PRUEBA,
            email='del-usuario@example.com', is_staff=True,
        )

    def test_usa_el_email_del_usuario_por_defecto(self):
        call_command('habilitar_2fa', 'otra_admin')
        device = EmailDevice.objects.get(user=self.user, name='default')
        self.assertTrue(device.confirmed)
        self.assertEqual(device.email or self.user.email, 'del-usuario@example.com')

    def test_permite_forzar_un_email_distinto(self):
        call_command('habilitar_2fa', 'otra_admin', '--email=lmveweb@gmail.com')
        device = EmailDevice.objects.get(user=self.user, name='default')
        self.assertEqual(device.email, 'lmveweb@gmail.com')

    def test_usuario_inexistente_falla_con_mensaje_claro(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command('habilitar_2fa', 'no-existe')
