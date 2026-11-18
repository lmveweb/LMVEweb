"""Tests del acceso al panel: el ingreso en dos pasos, "recordar este
computador", el grupo Editores y la creación de cuentas."""

import re
import time
from datetime import date
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_email.models import EmailDevice

from .acceso import COOKIE_RECORDAR, GRUPO_EDITORES, PENDIENTE, SEGUNDOS_PENDIENTE, SEGUNDOS_RECORDAR
from .models import MensajePatrocinio, Noticia
from LMVEweb.urls import ADMIN_URL

PANEL = f'/{ADMIN_URL}'
LOGIN_URL = f'{PANEL}login/'
CLAVE = 'clave-de-prueba-para-tests-9f2c'

# El cifrado real de las claves es lento a propósito (frena a quien las
# prueba de a miles); acá se entra cientos de veces, así que los tests
# usan uno rápido. No cambia lo que se prueba.
claves_rapidas = override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])


@claves_rapidas
class IngresoEnDosPasosTests(TestCase):
    """Paso 1: usuario y contraseña (el código sale solo). Paso 2: el
    código. Sin los dos, no hay sesión en el panel."""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            'carla', password=CLAVE, email='carla@example.com', is_staff=True, is_superuser=True,
        )
        self.device = EmailDevice.objects.create(user=self.user, name='default', confirmed=True)

    def _clave(self, cliente=None, username='carla', password=CLAVE, **extra):
        return (cliente or self.client).post(LOGIN_URL, {'username': username, 'password': password, **extra})

    def _codigo(self, codigo=None, cliente=None, **extra):
        if codigo is None:
            self.device.refresh_from_db()
            codigo = self.device.token
        return (cliente or self.client).post(LOGIN_URL, {'paso': 'codigo', 'codigo': codigo, **extra})

    def _adentro(self, cliente=None):
        return (cliente or self.client).get(PANEL).status_code == 200

    # --- Paso 1 ---

    def test_con_la_clave_correcta_el_codigo_sale_solo(self):
        r = self._clave()
        self.assertRedirects(r, LOGIN_URL, fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['carla@example.com'])
        self.device.refresh_from_db()
        self.assertIn(self.device.token, mail.outbox[0].body)
        # Todavía afuera: falta el código.
        self.assertFalse(self._adentro())

    def test_el_segundo_paso_pide_solo_el_codigo(self):
        self._clave()
        html = self.client.get(LOGIN_URL).content.decode()
        self.assertIn('name="codigo"', html)
        self.assertNotIn('name="password"', html)
        # El correo se muestra a medias, y la clave no viaja de vuelta.
        self.assertIn('ca•••@example.com', html)
        self.assertNotIn('carla@example.com', html)
        self.assertNotIn(CLAVE, html)

    def test_con_la_clave_mala_no_se_envia_nada(self):
        r = self._clave(password='mala')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn('name="password"', r.content.decode())

    def test_una_cuenta_sin_acceso_al_panel_no_recibe_codigo(self):
        visita = User.objects.create_user('visita', password=CLAVE, email='visita@example.com')
        EmailDevice.objects.create(user=visita, name='default', confirmed=True)
        self.assertEqual(self._clave(username='visita').status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_una_cuenta_sin_codigo_activado_no_entra(self):
        self.device.delete()
        r = self._clave()
        self.assertEqual(r.status_code, 200)
        self.assertIn('no tiene activado el código', r.content.decode())
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(self._adentro())

    def test_un_dispositivo_sin_confirmar_no_cuenta(self):
        EmailDevice.objects.filter(pk=self.device.pk).update(confirmed=False)
        self._clave()
        self.assertEqual(len(mail.outbox), 0)
        self.assertFalse(self._adentro())

    # --- Paso 2 ---

    def test_con_el_codigo_correcto_entra(self):
        self._clave()
        r = self._codigo()
        self.assertRedirects(r, PANEL, fetch_redirect_response=False)
        self.assertTrue(self._adentro())

    def test_el_codigo_se_acepta_con_espacios(self):
        self._clave()
        self.device.refresh_from_db()
        codigo = self.device.token
        self._codigo(f' {codigo[:3]} {codigo[3:]} ')
        self.assertTrue(self._adentro())

    def test_con_un_codigo_malo_no_entra(self):
        self._clave()
        r = self._codigo('000000')
        self.assertEqual(r.status_code, 200)
        self.assertIn('no es correcto', r.content.decode())
        self.assertFalse(self._adentro())

    def test_un_codigo_sirve_una_sola_vez(self):
        self._clave()
        self.device.refresh_from_db()
        codigo = self.device.token
        self._codigo(codigo)
        otro = Client()
        self._clave(otro)  # dentro del minuto de espera: no sale un código nuevo
        self._codigo(codigo, otro)
        self.assertFalse(self._adentro(otro))

    def test_el_codigo_solo_no_alcanza_sin_haber_pasado_la_clave(self):
        self.device.generate_challenge()
        r = self._codigo()
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self._adentro())

    def test_el_codigo_de_otra_persona_no_sirve(self):
        otra = User.objects.create_user('otra', password=CLAVE, email='otra@example.com', is_staff=True)
        ajeno = EmailDevice.objects.create(user=otra, name='default', confirmed=True)
        ajeno.generate_challenge()
        self._clave()
        ajeno.refresh_from_db()
        self._codigo(ajeno.token)
        self.assertFalse(self._adentro())

    def test_el_segundo_paso_vence_a_los_diez_minutos(self):
        self._clave()
        sesion = self.client.session
        pendiente = sesion[PENDIENTE]
        pendiente['desde'] -= SEGUNDOS_PENDIENTE + 1
        sesion[PENDIENTE] = pendiente
        sesion.save()
        self._codigo()
        self.assertFalse(self._adentro())
        self.assertIn('name="password"', self.client.get(LOGIN_URL).content.decode())

    def test_si_desactivan_la_cuenta_entre_los_dos_pasos_no_entra(self):
        self._clave()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self._codigo()
        self.assertFalse(self._adentro())

    def test_si_le_quitan_el_acceso_al_panel_entre_los_dos_pasos_no_entra(self):
        self._clave()
        User.objects.filter(pk=self.user.pk).update(is_staff=False)
        self._codigo()
        self.assertFalse(self._adentro())

    def test_si_cambia_la_clave_entre_los_dos_pasos_no_entra(self):
        self._clave()
        self.user.set_password('otra-clave-distinta-77x')
        self.user.save()
        self._codigo()
        self.assertFalse(self._adentro())

    def test_muchos_codigos_malos_bloquean_por_un_rato(self):
        self._clave()
        self._codigo('000000')
        # Tras un intento fallido hay que esperar: ni el código bueno pasa.
        r = self._codigo()
        self.assertIn('Demasiados intentos', r.content.decode())
        self.assertFalse(self._adentro())

    # --- Reenviar y cancelar ---

    def test_reenviar_respeta_el_minuto_de_espera(self):
        self._clave()
        self.client.post(LOGIN_URL, {'paso': 'reenviar'})
        self.assertEqual(len(mail.outbox), 1)
        self.device.refresh_from_db()
        self.device.cooldown_reset()
        self.client.post(LOGIN_URL, {'paso': 'reenviar'})
        self.assertEqual(len(mail.outbox), 2)

    def test_reenviar_sin_haber_pasado_la_clave_no_envia_nada(self):
        self.client.post(LOGIN_URL, {'paso': 'reenviar'})
        self.assertEqual(len(mail.outbox), 0)

    def test_si_falla_el_correo_se_puede_reintentar_al_tiro(self):
        with patch.object(EmailDevice, 'send_mail', side_effect=OSError('sin conexión')):
            with self.assertLogs('core.acceso', level='ERROR'):
                self._clave()
        self.assertIn('No pudimos enviarte', self.client.get(LOGIN_URL).content.decode())
        self.client.post(LOGIN_URL, {'paso': 'reenviar'})
        self.assertEqual(len(mail.outbox), 1)

    def test_entrar_con_otra_cuenta_vuelve_al_primer_paso(self):
        self._clave()
        self.client.post(LOGIN_URL, {'paso': 'cancelar'})
        self.assertIn('name="password"', self.client.get(LOGIN_URL).content.decode())
        self._codigo()
        self.assertFalse(self._adentro())

    # --- A dónde lleva al entrar ---

    def test_vuelve_a_la_pagina_que_se_queria_ver(self):
        destino = reverse('admin:core_noticia_changelist')
        self.client.post(f'{LOGIN_URL}?next={destino}', {'username': 'carla', 'password': CLAVE, 'next': destino})
        self.assertRedirects(self._codigo(), destino, fetch_redirect_response=False)

    def test_no_redirige_a_otro_sitio(self):
        self._clave(next='https://sitio-malo.example/robar')
        self.assertRedirects(self._codigo(), PANEL, fetch_redirect_response=False)

    def test_quien_ya_entro_no_ve_el_login_de_nuevo(self):
        self._clave()
        self._codigo()
        self.assertRedirects(self.client.get(LOGIN_URL), PANEL, fetch_redirect_response=False)


@claves_rapidas
class RecordarEsteComputadorTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user('carla', password=CLAVE, email='carla@example.com', is_staff=True)
        self.device = EmailDevice.objects.create(user=self.user, name='default', confirmed=True)

    def _entrar(self, recordar=True, username='carla'):
        """Ingreso completo desde un navegador nuevo. Devuelve la cookie
        que quedó (o None)."""
        cliente = Client()
        cliente.post(LOGIN_URL, {'username': username, 'password': CLAVE})
        device = EmailDevice.objects.get(user__username=username)
        datos = {'paso': 'codigo', 'codigo': device.token}
        if recordar:
            datos['recordar'] = 'on'
        r = cliente.post(LOGIN_URL, datos)
        device.cooldown_reset()
        return r.cookies.get(COOKIE_RECORDAR)

    def _volver(self, cookie, username='carla', clave=CLAVE):
        """Otro día, mismo computador: navegador sin sesión pero con la
        cookie. Devuelve (entró directo, llegó un correo nuevo)."""
        cliente = Client()
        if cookie is not None:
            cliente.cookies[COOKIE_RECORDAR] = cookie if isinstance(cookie, str) else cookie.value
        antes = len(mail.outbox)
        cliente.post(LOGIN_URL, {'username': username, 'password': clave})
        return cliente.get(PANEL).status_code == 200, len(mail.outbox) > antes

    def test_sin_marcar_la_casilla_no_queda_nada(self):
        self.assertIsNone(self._entrar(recordar=False))
        self.assertEqual(self._volver(None), (False, True))

    def test_la_cookie_dura_30_dias_y_no_la_lee_el_javascript(self):
        cookie = self._entrar()
        self.assertEqual(cookie['max-age'], SEGUNDOS_RECORDAR)
        self.assertEqual(SEGUNDOS_RECORDAR, 30 * 24 * 60 * 60)
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'Strict')
        self.assertEqual(cookie['path'], PANEL)

    def test_un_computador_recordado_entra_solo_con_la_clave(self):
        cookie = self._entrar()
        self.assertEqual(self._volver(cookie), (True, False))

    def test_recordado_igual_necesita_la_clave_correcta(self):
        cookie = self._entrar()
        self.assertEqual(self._volver(cookie, clave='mala'), (False, False))

    def test_la_cookie_de_otra_persona_no_sirve(self):
        otra = User.objects.create_user('otra', password=CLAVE, email='otra@example.com', is_staff=True)
        EmailDevice.objects.create(user=otra, name='default', confirmed=True)
        cookie = self._entrar(username='otra')
        self.assertEqual(self._volver(cookie), (False, True))

    def test_una_cookie_adulterada_no_sirve(self):
        valor = self._entrar().value
        self.assertEqual(self._volver(valor[:-3] + 'abc'), (False, True))
        EmailDevice.objects.get(user=self.user).cooldown_reset()  # el minuto de espera entre códigos
        self.assertEqual(self._volver('cualquier-cosa'), (False, True))

    def test_vence_a_los_30_dias(self):
        cookie = self._entrar()
        despues = time.time() + SEGUNDOS_RECORDAR + 60
        with patch('django.core.signing.time.time', return_value=despues):
            entro, _ = self._volver(cookie)
        self.assertFalse(entro)

    def test_cambiar_la_clave_olvida_los_computadores_recordados(self):
        cookie = self._entrar()
        self.user.set_password('clave-nueva-distinta-55k')
        self.user.save()
        self.assertEqual(self._volver(cookie, clave='clave-nueva-distinta-55k'), (False, True))

    def test_una_cuenta_desactivada_no_entra_aunque_este_recordada(self):
        cookie = self._entrar()
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertEqual(self._volver(cookie), (False, False))

    def test_sin_el_codigo_activado_no_entra_aunque_este_recordada(self):
        cookie = self._entrar()
        self.device.delete()
        self.assertEqual(self._volver(cookie), (False, False))


def entrar_al_panel(cliente, usuario):
    """Sesión con el código ya verificado (el ingreso real se prueba arriba)."""
    dispositivo, _ = EmailDevice.objects.get_or_create(user=usuario, name='default', defaults={'confirmed': True})
    cliente.force_login(usuario)
    sesion = cliente.session
    sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
    sesion.save()


@claves_rapidas
class GrupoEditoresTests(TestCase):
    """Un editor hace todo con las noticias y nada más. Cada test de
    "no puede" intenta saltarse la restricción yendo directo a la
    dirección, no solo mirando que falte el enlace."""

    def setUp(self):
        self.editor = User.objects.create_user(
            'editora', password=CLAVE, email='editora@example.com',
            first_name='Carla', last_name='González', is_staff=True,
        )
        self.editor.groups.add(Group.objects.get(name=GRUPO_EDITORES))
        entrar_al_panel(self.client, self.editor)
        self.jefa = User.objects.create_superuser('jefa', 'jefa@example.com', CLAVE)
        self.mensaje = MensajePatrocinio.objects.create(
            nombre='Juana', institucion='Acme', email='juana@acme.cl', mensaje='Hola',
        )
        self.noticia = Noticia.objects.create(
            titulo='Final de la Copa', fecha=date(2026, 11, 1), resumen='Resumen.', cuerpo='Texto.',
        )

    def _noticia_post(self, **extra):
        return {
            'titulo': 'Nueva noticia', 'fecha': '14/11/2026', 'autor': 'Carla González',
            'resumen': 'Resumen.', 'cuerpo': 'Texto.',
            'fotos-TOTAL_FORMS': '0', 'fotos-INITIAL_FORMS': '0',
            'fotos-MIN_NUM_FORMS': '0', 'fotos-MAX_NUM_FORMS': '8',
            **extra,
        }

    def test_el_grupo_existe_con_los_permisos_justos(self):
        permisos = set(Group.objects.get(name=GRUPO_EDITORES).permissions.values_list(
            'content_type__app_label', 'codename',
        ))
        esperados = {
            ('core', f'{accion}_{modelo}')
            for modelo in ('noticia', 'fotonoticia')
            for accion in ('add', 'change', 'delete', 'view')
        }
        self.assertEqual(permisos, esperados)

    # --- Lo que sí puede ---

    def test_ve_solo_noticias_en_el_inicio_del_panel(self):
        html = self.client.get(PANEL).content.decode()
        self.assertIn(reverse('admin:core_noticia_changelist'), html)
        self.assertNotIn(reverse('admin:core_mensajepatrocinio_changelist'), html)
        self.assertNotIn(reverse('admin:auth_user_changelist'), html)
        self.assertNotIn(reverse('admin:auth_group_changelist'), html)

    def test_puede_crear_una_noticia(self):
        r = self.client.post(reverse('admin:core_noticia_add'), self._noticia_post())
        self.assertEqual(r.status_code, 302, r.content.decode()[:2000] if r.status_code == 200 else '')
        self.assertTrue(Noticia.objects.filter(titulo='Nueva noticia').exists())

    def test_una_noticia_nueva_parte_firmada_con_su_nombre(self):
        html = self.client.get(reverse('admin:core_noticia_add')).content.decode()
        self.assertIn('value="Carla González"', html)

    def test_puede_editar_y_despublicar(self):
        url = reverse('admin:core_noticia_change', args=[self.noticia.pk])
        r = self.client.post(url, self._noticia_post(titulo='Título corregido'))
        self.assertEqual(r.status_code, 302)
        self.noticia.refresh_from_db()
        self.assertEqual(self.noticia.titulo, 'Título corregido')
        self.assertFalse(self.noticia.publicada)

    def test_puede_borrar_una_noticia(self):
        url = reverse('admin:core_noticia_delete', args=[self.noticia.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 302)
        self.assertFalse(Noticia.objects.filter(pk=self.noticia.pk).exists())

    def test_puede_cambiar_su_propia_clave(self):
        self.assertEqual(self.client.get(reverse('admin:password_change')).status_code, 200)

    # --- Lo que no puede ---

    def test_no_puede_ver_ni_tocar_los_mensajes_de_contacto(self):
        for nombre, args in [
            ('admin:core_mensajepatrocinio_changelist', []),
            ('admin:core_mensajepatrocinio_add', []),
            ('admin:core_mensajepatrocinio_change', [self.mensaje.pk]),
            ('admin:core_mensajepatrocinio_delete', [self.mensaje.pk]),
            ('admin:core_mensajepatrocinio_history', [self.mensaje.pk]),
        ]:
            with self.subTest(nombre):
                url = reverse(nombre, args=args)
                self.assertEqual(self.client.get(url).status_code, 403)
                self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 403)
        self.assertTrue(MensajePatrocinio.objects.filter(pk=self.mensaje.pk).exists())

    def test_no_puede_ver_ni_crear_cuentas(self):
        for nombre, args in [
            ('admin:auth_user_changelist', []),
            ('admin:auth_user_add', []),
            ('admin:auth_user_change', [self.jefa.pk]),
            ('admin:auth_user_delete', [self.jefa.pk]),
            ('admin:auth_user_password_change', [self.jefa.pk]),
            ('admin:auth_group_changelist', []),
            ('admin:auth_group_add', []),
            ('admin:auth_group_change', [Group.objects.get(name=GRUPO_EDITORES).pk]),
        ]:
            with self.subTest(nombre):
                self.assertEqual(self.client.get(reverse(nombre, args=args)).status_code, 403)

    def test_no_puede_crear_una_cuenta_por_post(self):
        r = self.client.post(reverse('admin:auth_user_add'), {
            'username': 'intruso', 'password1': CLAVE, 'password2': CLAVE,
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(User.objects.filter(username='intruso').exists())

    def test_no_puede_hacerse_administrador(self):
        r = self.client.post(reverse('admin:auth_user_change', args=[self.editor.pk]), {
            'username': 'editora', 'is_active': 'on', 'is_staff': 'on', 'is_superuser': 'on',
        })
        self.assertEqual(r.status_code, 403)
        self.editor.refresh_from_db()
        self.assertFalse(self.editor.is_superuser)

    def test_no_puede_cambiarle_la_clave_a_quien_administra(self):
        r = self.client.post(reverse('admin:auth_user_password_change', args=[self.jefa.pk]), {
            'password1': 'clave-robada-123x', 'password2': 'clave-robada-123x',
        })
        self.assertEqual(r.status_code, 403)
        self.jefa.refresh_from_db()
        self.assertTrue(self.jefa.check_password(CLAVE))

    def test_no_puede_darle_permisos_a_su_grupo(self):
        grupo = Group.objects.get(name=GRUPO_EDITORES)
        antes = grupo.permissions.count()
        r = self.client.post(reverse('admin:auth_group_change', args=[grupo.pk]), {'name': GRUPO_EDITORES})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(grupo.permissions.count(), antes)

    def test_no_puede_activarle_el_codigo_a_nadie(self):
        r = self.client.post(reverse('admin:auth_user_changelist'), {
            'action': 'activar_codigo', '_selected_action': [self.jefa.pk],
        })
        self.assertEqual(r.status_code, 403)
        self.assertFalse(EmailDevice.objects.filter(user=self.jefa).exists())

    # --- Lo que le pueden quitar ---

    def test_sin_el_codigo_verificado_no_entra_al_panel(self):
        cliente = Client()
        cliente.force_login(self.editor)
        self.assertEqual(cliente.get(reverse('admin:core_noticia_changelist')).status_code, 302)

    def test_al_desactivar_la_cuenta_queda_afuera_al_tiro(self):
        User.objects.filter(pk=self.editor.pk).update(is_active=False)
        self.assertEqual(self.client.get(reverse('admin:core_noticia_changelist')).status_code, 302)

    def test_al_sacarla_del_grupo_ya_no_ve_las_noticias(self):
        self.editor.groups.clear()
        self.assertEqual(self.client.get(reverse('admin:core_noticia_changelist')).status_code, 403)


@claves_rapidas
class CuentasDesdeElPanelTests(TestCase):
    """Quien administra activa el código por correo desde la lista de
    usuarios, sin pasar por la consola del hosting."""

    def setUp(self):
        self.jefa = User.objects.create_superuser('jefa', 'jefa@example.com', CLAVE)
        entrar_al_panel(self.client, self.jefa)
        self.url = reverse('admin:auth_user_changelist')

    def _activar(self, *usuarios):
        return self.client.post(self.url, {
            'action': 'activar_codigo', '_selected_action': [u.pk for u in usuarios],
        }, follow=True)

    def test_activa_el_codigo_al_correo_de_la_ficha(self):
        nueva = User.objects.create_user('nueva', password=CLAVE, email='nueva@example.com', is_staff=True)
        r = self._activar(nueva)
        self.assertIn('nueva@example.com', r.content.decode())
        device = EmailDevice.objects.get(user=nueva)
        self.assertTrue(device.confirmed)
        # Sin correo propio: sigue al de la ficha si después se cambia.
        self.assertFalse(device.email)

    def test_sin_correo_en_la_ficha_no_activa_nada(self):
        nueva = User.objects.create_user('nueva', password=CLAVE, is_staff=True)
        r = self._activar(nueva)
        self.assertIn('no tiene correo', r.content.decode())
        self.assertFalse(EmailDevice.objects.filter(user=nueva).exists())

    def test_no_pisa_un_correo_aparte_ya_configurado(self):
        EmailDevice.objects.filter(user=self.jefa).update(email='aparte@example.com', confirmed=False)
        self._activar(self.jefa)
        device = EmailDevice.objects.get(user=self.jefa, email='aparte@example.com')
        self.assertTrue(device.confirmed)

    def test_la_lista_muestra_quien_tiene_el_codigo_activado(self):
        self.assertIn('Código por correo', self.client.get(self.url).content.decode())


@claves_rapidas
class CrearEditorCommandTests(TestCase):
    def _crear(self, username='cgonzalez', **extra):
        opciones = {'nombre': 'Carla', 'apellido': 'González', 'email': 'carla@example.com', **extra}
        salida = StringIO()
        call_command('crear_editor', username, stdout=salida, **opciones)
        return salida.getvalue()

    def test_deja_la_cuenta_lista_para_entrar(self):
        salida = self._crear()
        user = User.objects.get(username='cgonzalez')
        self.assertEqual(user.get_full_name(), 'Carla González')
        self.assertEqual(user.email, 'carla@example.com')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), [GRUPO_EDITORES])
        self.assertTrue(EmailDevice.objects.get(user=user).confirmed)
        clave = re.search(r'Clave temporal:\s+(\S+)', salida).group(1)
        self.assertTrue(user.check_password(clave))

    def test_la_cuenta_creada_entra_con_los_dos_pasos_y_solo_ve_noticias(self):
        cache.clear()
        clave = re.search(r'Clave temporal:\s+(\S+)', self._crear()).group(1)
        self.client.post(LOGIN_URL, {'username': 'cgonzalez', 'password': clave})
        self.assertEqual(mail.outbox[0].to, ['carla@example.com'])
        codigo = EmailDevice.objects.get(user__username='cgonzalez').token
        self.client.post(LOGIN_URL, {'paso': 'codigo', 'codigo': codigo})
        self.assertEqual(self.client.get(reverse('admin:core_noticia_changelist')).status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:auth_user_changelist')).status_code, 403)

    def test_cada_clave_temporal_es_distinta_y_pasa_las_reglas_de_django(self):
        from django.contrib.auth.password_validation import validate_password
        from .acceso import clave_temporal
        claves = {clave_temporal() for _ in range(50)}
        self.assertEqual(len(claves), 50)
        for clave in claves:
            validate_password(clave)
            self.assertRegex(clave, r'^[a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4}$')

    def test_no_pisa_una_cuenta_que_ya_existe(self):
        User.objects.create_superuser('Jefa', 'jefa@example.com', CLAVE)
        with self.assertRaises(CommandError):
            self._crear('jefa')
        self.assertTrue(User.objects.get(username='Jefa').check_password(CLAVE))

    def test_un_correo_mal_escrito_falla_sin_crear_nada(self):
        with self.assertRaises(CommandError):
            self._crear(email='carla@')
        self.assertFalse(User.objects.filter(username='cgonzalez').exists())
