from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from .models import MensajePatrocinio


def datos_validos(**overrides):
    datos = {
        'nombre': 'Juana Pérez',
        'institucion': 'Colegio Acme',
        'email': 'juana@acme.cl',
        'mensaje': 'Nos interesa auspiciar la temporada 2026.',
        'acepta_politica': 'on',
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

    def test_envio_exitoso(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])

        self.assertEqual(MensajePatrocinio.objects.count(), 1)
        mensaje = MensajePatrocinio.objects.get()
        self.assertEqual(mensaje.nombre, 'Juana Pérez')
        self.assertEqual(mensaje.institucion, 'Colegio Acme')
        self.assertEqual(mensaje.email, 'juana@acme.cl')

        # Sin CONTACTO_DESTINATARIO configurado en el entorno de test, no
        # se intenta mandar correo (y el guardado del mensaje no depende
        # de que el envío funcione).
        self.assertEqual(len(mail.outbox), 0)


class RutasTests(TestCase):
    def test_staff_disponible(self):
        self.assertEqual(self.client.get(reverse('staff')).status_code, 200)

    def test_privacidad_disponible(self):
        self.assertEqual(self.client.get(reverse('privacidad')).status_code, 200)

    def test_impacto_ya_no_existe(self):
        with self.assertRaises(NoReverseMatch):
            reverse('impacto')
