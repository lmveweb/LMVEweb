import time
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.signing import Signer
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, reverse

from .antispam import SALT_MARCA_TIEMPO, SEGUNDOS_MINIMOS
from .models import MensajePatrocinio


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
