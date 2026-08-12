from django.core import mail
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import MensajePatrocinio


def datos_validos(**overrides):
    datos = {
        'empresa': 'Acme SpA',
        'contacto': 'Juana Pérez',
        'email': 'juana@acme.cl',
        'interes': 'naming',
        'mensaje': 'Nos interesa auspiciar la temporada 2026.',
    }
    datos.update(overrides)
    return datos


class ContactoTests(TestCase):
    def setUp(self):
        # El rate limiting (Tanda 6) usa la misma cache entre tests; sin
        # esto, un test podría heredar los intentos consumidos por otro.
        cache.clear()

    def test_falta_campo_obligatorio(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(empresa=''))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_email_invalido(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(email='no-es-un-correo'))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_interes_invalido(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos(interes='no-existe'))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_campo_excede_el_maximo_de_caracteres(self):
        empresa_muy_larga = 'A' * 201  # el modelo permite hasta 200
        respuesta = self.client.post(reverse('contacto'), datos_validos(empresa=empresa_muy_larga))
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.json()['ok'])
        self.assertEqual(MensajePatrocinio.objects.count(), 0)

    def test_envio_exitoso(self):
        respuesta = self.client.post(reverse('contacto'), datos_validos())
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()['ok'])

        self.assertEqual(MensajePatrocinio.objects.count(), 1)
        mensaje = MensajePatrocinio.objects.get()
        self.assertEqual(mensaje.empresa, 'Acme SpA')
        self.assertEqual(mensaje.email, 'juana@acme.cl')

        # Sin CONTACTO_DESTINATARIO configurado en el entorno de test, no
        # se intenta mandar correo (y el guardado del mensaje no depende
        # de que el envío funcione).
        self.assertEqual(len(mail.outbox), 0)
