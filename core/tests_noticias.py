"""Tests de Noticias: el modelo, el procesado de fotos, las vistas
públicas, el SEO y el formulario del admin."""

import io
import json
import re
from datetime import date

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django_otp import DEVICE_ID_SESSION_KEY
from django_otp.plugins.otp_email.models import EmailDevice
from PIL import Image

from .admin import FotoNoticiaForm, NoticiaAdmin, site
from .imagenes import GRANDE, MINIATURA, FotoInvalida, imagen_social, procesar_foto
from .models import FotoNoticia, Noticia
from .templatetags.noticias import cuerpo_noticia


def foto_de_celular(ancho=2400, alto=1800, formato='JPEG', con_gps=True, orientacion=None):
    """Una foto como la que sale de un celular: grande y con metadatos
    EXIF, incluida la ubicación GPS."""
    imagen = Image.new('RGB', (ancho, alto), (40, 110, 180))
    exif = Image.Exif()
    exif[0x010F] = 'MarcaDePrueba'          # fabricante
    exif[0x0110] = 'Telefono X'             # modelo
    if orientacion:
        exif[0x0112] = orientacion
    if con_gps:
        gps = exif.get_ifd(0x8825)
        gps[1], gps[2] = 'S', (33.0, 27.0, 0.0)   # latitud de Santiago
        gps[3], gps[4] = 'W', (70.0, 40.0, 0.0)
    salida = io.BytesIO()
    imagen.save(salida, formato, **({'exif': exif} if formato != 'PNG' else {}))
    return SimpleUploadedFile(f'foto.{formato.lower()}', salida.getvalue(), content_type=f'image/{formato.lower()}')


def crear_noticia(titulo='Éxito de la Copa Milled', publicada=True, fotos=0, **extra):
    datos = {
        'titulo': titulo, 'resumen': 'Resumen de la noticia.', 'cuerpo': 'Primer párrafo.',
        'fecha': date(2026, 11, 11), 'publicada': publicada,
    }
    datos.update(extra)
    noticia = Noticia.objects.create(**datos)
    for i in range(fotos):
        foto = FotoNoticia(noticia=noticia, orden=i, alt=f'Foto {i + 1} de la premiación')
        foto.cargar(procesar_foto(foto_de_celular(ancho=1200 + i, alto=900)))
        foto.save()
    return noticia


class TextoDeLaNoticiaTests(TestCase):
    def test_parrafos_listas_y_subtitulos(self):
        html = cuerpo_noticia(
            'Primer párrafo\nsegunda línea.\n\nOtro párrafo.\n\n'
            '# Cuadro de Honor\nCategoría Damas:\n1. Colegio Andrée\n2. Liceo Manuel de Salas\n\n'
            '- Milled\n· Molten\n'
        )
        self.assertIn('<p>Primer párrafo<br>segunda línea.</p>', html)
        self.assertIn('<p>Otro párrafo.</p>', html)
        self.assertIn('<h2>Cuadro de Honor</h2>', html)
        self.assertIn('<p>Categoría Damas:</p>', html)
        self.assertIn('<ol><li>Colegio Andrée</li><li>Liceo Manuel de Salas</li></ol>', html)
        self.assertIn('<ul><li>Milled</li><li>Molten</li></ul>', html)

    def test_no_deja_pasar_html_ni_scripts(self):
        # Aunque le roben la cuenta a un editor, por el texto de una
        # noticia no puede entrar código al sitio.
        html = cuerpo_noticia(
            '<script>alert(1)</script>\n\n- <img src=x onerror=alert(1)>\n\n# <b>hola</b>\n\n'
            '<a href="javascript:alert(1)">clic</a>'
        )
        for etiqueta in ('<script', '<img', '<b>', '<a '):
            self.assertNotIn(etiqueta, html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)

    def test_la_pagina_muestra_el_texto_escapado(self):
        noticia = crear_noticia(titulo='<i>Título</i>', resumen='<u>resumen</u>',
                                cuerpo='<script>alert(1)</script>')
        html = self.client.get(noticia.get_absolute_url()).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('<i>Título</i>', html)
        self.assertNotIn('<u>resumen</u>', html)


class EnlacesIncrustadosTests(TestCase):
    """Un enlace pegado solo en una línea: YouTube e Instagram se
    incrustan; cualquier otro queda como botón."""

    def test_youtube_en_todas_sus_formas_se_incrusta_sin_cookies(self):
        for url in (
            'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://youtube.com/watch?feature=share&v=dQw4w9WgXcQ&t=30s',
            'https://youtu.be/dQw4w9WgXcQ?si=abc123',
            'https://m.youtube.com/watch?v=dQw4w9WgXcQ',
            'https://www.youtube.com/live/dQw4w9WgXcQ',
            'https://www.youtube.com/embed/dQw4w9WgXcQ',
        ):
            with self.subTest(url=url):
                html = cuerpo_noticia(f'Miren el partido:\n\n{url}\n\nGracias.')
                self.assertIn('<iframe src="https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"', html)
                self.assertIn('referrerpolicy="strict-origin-when-cross-origin"', html)
                self.assertIn('title="Video de YouTube"', html)
                self.assertIn('<p>Miren el partido:</p>', html)
                self.assertIn('<p>Gracias.</p>', html)

    def test_un_short_de_youtube_va_en_formato_vertical(self):
        html = cuerpo_noticia('https://www.youtube.com/shorts/dQw4w9WgXcQ')
        self.assertIn('class="noticia-video noticia-video--vertical"', html)
        self.assertIn('/embed/dQw4w9WgXcQ"', html)

    def test_instagram_se_incrusta_con_el_mismo_marcado_de_la_portada(self):
        for url, permalink in (
            ('https://www.instagram.com/p/Dap8UmUEZdM/?utm_source=ig_web', 'https://www.instagram.com/p/Dap8UmUEZdM/'),
            ('https://instagram.com/reel/DblC_A0DImu/', 'https://www.instagram.com/reel/DblC_A0DImu/'),
            ('https://www.instagram.com/ligametropolitanavoley/p/DZeAWx5DOI3/', 'https://www.instagram.com/p/DZeAWx5DOI3/'),
        ):
            with self.subTest(url=url):
                html = cuerpo_noticia(url)
                self.assertIn(f'<blockquote class="instagram-media" data-instgrm-permalink="{permalink}"', html)

    def test_otras_redes_quedan_como_boton_que_abre_en_otra_pestana(self):
        html = cuerpo_noticia('https://www.tiktok.com/@liga/video/7301234567890123456')
        self.assertIn('<a class="noticia-enlace" href="https://www.tiktok.com/@liga/video/7301234567890123456" '
                      'target="_blank" rel="noopener noreferrer">Ver en TikTok</a>', html)
        self.assertNotIn('<iframe', html)
        self.assertIn('>Ver en ejemplo.cl</a>', cuerpo_noticia('https://www.ejemplo.cl/bases.pdf'))

    def test_un_enlace_dentro_de_una_frase_queda_clicable_sin_comerse_el_punto(self):
        html = cuerpo_noticia('Las bases están en https://ligamve.cl/bases?a=1&b=2. ¡Inscríbanse!')
        self.assertIn('<a href="https://ligamve.cl/bases?a=1&amp;b=2" target="_blank" rel="noopener noreferrer">'
                      'https://ligamve.cl/bases?a=1&amp;b=2</a>. ¡Inscríbanse!', html)
        self.assertNotIn('<iframe', html)
        # Un video mencionado dentro de una frase no se incrusta: solo
        # cuando el enlace va solo en su línea.
        self.assertNotIn('<iframe', cuerpo_noticia('Vean https://youtu.be/dQw4w9WgXcQ por favor'))

    def test_un_enlace_no_sirve_para_colar_codigo(self):
        for texto in (
            'javascript:alert(1)',
            'https://youtu.be/dQw4w9WgXcQ"><script>alert(1)</script>',
            'https://www.youtube.com/watch?v=x"onload="alert(1)',
            'https://www.instagram.com/p/abc"><img src=x onerror=alert(1)>/',
            'https://ejemplo.cl/"onmouseover="alert(1)',
            'Texto con https://ejemplo.cl/"onmouseover="alert(1) adentro',
            'data:text/html,<script>alert(1)</script>',
        ):
            with self.subTest(texto=texto):
                html = cuerpo_noticia(texto)
                self.assertNotIn('<script', html)
                self.assertNotIn('<img', html)
                self.assertNotRegex(html, r'<[^>]*\son\w+=')       # ningún atributo onalgo=
                self.assertNotIn('href="javascript:', html)
                self.assertNotIn('href="data:', html)
                # Lo único que puede ir en un iframe es un id de YouTube válido.
                for src in re.findall(r'<iframe src="([^"]*)"', html):
                    self.assertRegex(src, r'^https://www\.youtube-nocookie\.com/embed/[A-Za-z0-9_-]{11}$')

    def test_la_pagina_carga_el_script_de_instagram_solo_si_hace_falta(self):
        sin = crear_noticia(titulo='Sin embed', cuerpo='Solo texto.\n\nhttps://youtu.be/dQw4w9WgXcQ')
        con = crear_noticia(titulo='Con embed', cuerpo='https://www.instagram.com/p/Dap8UmUEZdM/')
        r = self.client.get(sin.get_absolute_url())
        self.assertNotContains(r, 'instagram.com/embed.js')
        self.assertContains(r, 'youtube-nocookie.com/embed/dQw4w9WgXcQ')
        self.assertContains(self.client.get(con.get_absolute_url()),
                            '<script async src="https://www.instagram.com/embed.js"></script>')

    def test_la_politica_de_seguridad_permite_el_iframe_de_youtube_y_ningun_script_suyo(self):
        csp = self.client.get(crear_noticia().get_absolute_url())['Content-Security-Policy']
        directivas = dict(d.strip().split(' ', 1) for d in csp.split(';') if ' ' in d.strip())
        self.assertIn('www.youtube-nocookie.com', directivas['frame-src'])
        self.assertNotIn('youtube', directivas['script-src'])


class AutorTests(TestCase):
    def test_con_autor_la_noticia_muestra_quien_la_publico(self):
        noticia = crear_noticia(autor='Camila Busch')
        r = self.client.get(noticia.get_absolute_url())
        self.assertContains(r, '<span class="noticia-autor">Por Camila Busch</span>')
        datos = json.loads(re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                                     r.content.decode(), re.S).group(1))
        self.assertEqual(datos['author'], {'@type': 'Person', 'name': 'Camila Busch'})

    def test_sin_autor_no_aparece_la_firma_y_firma_la_liga(self):
        r = self.client.get(crear_noticia().get_absolute_url())
        self.assertNotContains(r, 'noticia-autor"')
        datos = json.loads(re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>',
                                     r.content.decode(), re.S).group(1))
        self.assertEqual(datos['author']['@type'], 'Organization')

    def test_el_nombre_del_autor_se_escapa(self):
        r = self.client.get(crear_noticia(autor='<b>Camila</b>').get_absolute_url())
        self.assertNotContains(r, '<b>Camila</b>')


class FotosTests(TestCase):
    def test_se_achica_a_dos_tamanos_en_webp(self):
        r = procesar_foto(foto_de_celular(2400, 1800))
        self.assertEqual((r['ancho'], r['alto']), (GRANDE, 1200))
        self.assertEqual((r['mini_ancho'], r['mini_alto']), (MINIATURA, 600))
        for clave in ('grande', 'miniatura'):
            self.assertEqual(Image.open(io.BytesIO(r[clave])).format, 'WEBP')

    def test_no_agranda_una_foto_chica(self):
        r = procesar_foto(foto_de_celular(640, 480))
        self.assertEqual((r['ancho'], r['alto']), (640, 480))
        self.assertEqual((r['mini_ancho'], r['mini_alto']), (640, 480))

    def test_no_conserva_ubicacion_gps_ni_ningun_otro_metadato(self):
        # Son fotos de menores: la ubicación del celular no puede quedar
        # publicada dentro del archivo.
        original = foto_de_celular()
        self.assertTrue(Image.open(original).getexif().get_ifd(0x8825), 'la foto de prueba no trae GPS')
        r = procesar_foto(original)
        for clave in ('grande', 'miniatura'):
            imagen = Image.open(io.BytesIO(r[clave]))
            self.assertEqual(len(imagen.getexif()), 0)
            self.assertNotIn('exif', imagen.info)
            self.assertNotIn('xmp', imagen.info)
            self.assertNotIn(b'MarcaDePrueba', r[clave])
        social = Image.open(io.BytesIO(imagen_social(r['grande'])))
        self.assertEqual(len(social.getexif()), 0)

    def test_respeta_la_orientacion_antes_de_borrar_los_metadatos(self):
        # Orientación 6 = foto tomada con el celular en vertical: el
        # archivo viene "acostado" y el EXIF dice que hay que girarlo.
        r = procesar_foto(foto_de_celular(2000, 1000, orientacion=6))
        self.assertGreater(r['alto'], r['ancho'])

    def test_png_con_transparencia_queda_sobre_blanco(self):
        imagen = Image.new('RGBA', (300, 200), (0, 0, 0, 0))
        salida = io.BytesIO()
        imagen.save(salida, 'PNG')
        r = procesar_foto(SimpleUploadedFile('logo.png', salida.getvalue()))
        self.assertEqual(Image.open(io.BytesIO(r['grande'])).convert('RGB').getpixel((10, 10)), (255, 255, 255))

    def test_rechaza_lo_que_no_es_una_foto(self):
        for nombre, contenido in [
            ('nota.jpg', b'esto no es una imagen'),
            ('pagina.jpg', b'<html><script>alert(1)</script></html>'),
            ('dibujo.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'),
        ]:
            with self.subTest(archivo=nombre), self.assertRaises(FotoInvalida):
                procesar_foto(SimpleUploadedFile(nombre, contenido))

    def test_rechaza_formatos_que_no_son_jpg_png_ni_webp(self):
        salida = io.BytesIO()
        Image.new('RGB', (50, 50)).save(salida, 'GIF')
        with self.assertRaises(FotoInvalida):
            procesar_foto(SimpleUploadedFile('animacion.gif', salida.getvalue()))

    def test_rechaza_un_archivo_de_mas_de_10_mb(self):
        archivo = foto_de_celular(100, 100)
        archivo.size = 11 * 1024 * 1024
        with self.assertRaisesMessage(FotoInvalida, '10 MB'):
            procesar_foto(archivo)

    def test_rechaza_una_imagen_con_demasiados_pixeles(self):
        # 9000 × 6000 = 54 megapíxeles, pero pesa pocos KB comprimida:
        # abrirla entera podría agotar la memoria del servidor.
        salida = io.BytesIO()
        Image.new('L', (9000, 6000)).save(salida, 'PNG')
        with self.assertRaisesMessage(FotoInvalida, 'demasiado grande'):
            procesar_foto(SimpleUploadedFile('enorme.png', salida.getvalue()))

    def test_imagen_social_es_jpeg_de_1200_por_630(self):
        social = Image.open(io.BytesIO(imagen_social(procesar_foto(foto_de_celular())['grande'])))
        self.assertEqual(social.format, 'JPEG')
        self.assertEqual(social.size, (1200, 630))


class NoticiaModeloTests(TestCase):
    def test_el_slug_sale_del_titulo_y_no_se_repite(self):
        a = crear_noticia(titulo='Éxito de la IV Copa Milled')
        b = crear_noticia(titulo='Éxito de la IV Copa Milled')
        self.assertEqual(a.slug, 'exito-de-la-iv-copa-milled')
        self.assertEqual(b.slug, 'exito-de-la-iv-copa-milled-2')

    def test_corregir_el_titulo_no_cambia_el_link(self):
        noticia = crear_noticia(titulo='Copa Miled')
        noticia.titulo = 'Copa Milled'
        noticia.save()
        self.assertEqual(Noticia.objects.get(pk=noticia.pk).slug, 'copa-miled')

    def test_un_titulo_sin_letras_igual_tiene_slug(self):
        self.assertEqual(crear_noticia(titulo='¡¡¡!!!').slug, 'noticia')

    def test_las_consultas_normales_no_traen_las_fotos(self):
        # Listar noticias no puede cargar megabytes de imágenes.
        crear_noticia(fotos=1)
        foto = FotoNoticia.objects.get()
        self.assertEqual(foto.get_deferred_fields(), {'miniatura', 'grande'})
        self.assertEqual(Noticia.objects.get().get_deferred_fields(), {'imagen_social'})


class NoticiasPublicasTests(TestCase):
    def test_la_lista_muestra_solo_las_publicadas_y_las_mas_nuevas_primero(self):
        crear_noticia(titulo='Noticia vieja', fecha=date(2026, 3, 1))
        crear_noticia(titulo='Noticia nueva', fecha=date(2026, 11, 1))
        crear_noticia(titulo='Borrador secreto', publicada=False)
        html = self.client.get(reverse('noticias')).content.decode()
        self.assertNotIn('Borrador secreto', html)
        self.assertLess(html.index('Noticia nueva'), html.index('Noticia vieja'))

    def test_la_lista_sin_noticias_lo_dice(self):
        self.assertContains(self.client.get(reverse('noticias')), 'Todavía no hay noticias publicadas')

    def test_la_lista_se_pagina_de_a_12(self):
        for i in range(13):
            crear_noticia(titulo=f'Noticia {i:02d}', fecha=date(2026, 1, 1 + i))
        primera = self.client.get(reverse('noticias')).content.decode()
        self.assertEqual(primera.count('class="noticia-card"'), 12)
        self.assertIn('?pagina=2', primera)
        segunda = self.client.get(reverse('noticias') + '?pagina=2').content.decode()
        self.assertEqual(segunda.count('class="noticia-card"'), 1)
        # Un número de página inventado no rompe: muestra la última.
        self.assertEqual(self.client.get(reverse('noticias') + '?pagina=999').status_code, 200)
        self.assertEqual(self.client.get(reverse('noticias') + '?pagina=abc').status_code, 200)

    def test_la_noticia_muestra_titulo_fecha_texto_y_fotos(self):
        noticia = crear_noticia(fotos=3, cuerpo='Gran torneo.\n\n1. Colegio Andrée')
        r = self.client.get(noticia.get_absolute_url())
        self.assertContains(r, 'Éxito de la Copa Milled')
        self.assertContains(r, '11 de noviembre de 2026')
        self.assertContains(r, '<ol><li>Colegio Andrée</li></ol>')
        html = r.content.decode()
        fotos = list(noticia.fotos.all())
        self.assertIn(f'src="{fotos[0].url_grande}"', html)       # la principal, grande
        for foto in fotos[1:]:
            self.assertIn(f'src="{foto.url_miniatura}"', html)    # el resto, en la galería
            self.assertIn(f'href="{foto.url_grande}"', html)
        self.assertIn('alt="Foto 1 de la premiación"', html)

    def test_un_borrador_no_existe_para_el_publico(self):
        noticia = crear_noticia(publicada=False, fotos=1)
        foto = noticia.fotos.get()
        self.assertEqual(self.client.get(noticia.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get(foto.url_miniatura).status_code, 404)
        self.assertEqual(self.client.get(foto.url_grande).status_code, 404)

    def test_quien_entro_al_panel_ve_el_borrador_como_vista_previa(self):
        noticia = crear_noticia(publicada=False, fotos=1)
        self.client.force_login(User.objects.create_user('editora', password='x', is_staff=True))
        r = self.client.get(noticia.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Borrador: esta noticia todavía no está publicada')
        self.assertContains(r, '<meta name="robots" content="noindex, follow">')
        self.assertNotContains(r, 'rel="canonical"')
        self.assertNotContains(r, 'application/ld+json')
        self.assertEqual(r['Cache-Control'], 'private, no-store')
        foto = self.client.get(noticia.fotos.get().url_miniatura)
        self.assertEqual(foto.status_code, 200)
        self.assertEqual(foto['Cache-Control'], 'private, no-store')

    def test_un_usuario_que_no_es_del_panel_no_ve_borradores(self):
        noticia = crear_noticia(publicada=False)
        self.client.force_login(User.objects.create_user('cualquiera', password='x'))
        self.assertEqual(self.client.get(noticia.get_absolute_url()).status_code, 404)

    def test_las_fotos_se_sirven_como_webp_y_se_guardan_un_anio(self):
        foto = crear_noticia(fotos=1).fotos.get()
        for url, lado in ((foto.url_miniatura, MINIATURA), (foto.url_grande, 1200)):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r['Content-Type'], 'image/webp')
            self.assertEqual(r['Cache-Control'], 'public, max-age=31536000, immutable')
            self.assertEqual(Image.open(io.BytesIO(r.content)).width, lado)

    def test_una_direccion_de_foto_con_version_vieja_o_tamano_inventado_da_404(self):
        foto = crear_noticia(fotos=1).fotos.get()
        self.assertEqual(self.client.get(reverse('noticia_foto', args=[foto.pk, 'abcdef123456', 'm'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('noticia_foto', args=[foto.pk, foto.version, 'x'])).status_code, 404)
        self.assertEqual(self.client.get(reverse('noticia_foto', args=[foto.pk + 99, foto.version, 'm'])).status_code, 404)

    def test_las_vistas_de_noticias_son_de_solo_lectura(self):
        noticia = crear_noticia(fotos=1)
        for url in (reverse('noticias'), noticia.get_absolute_url(), noticia.fotos.get().url_miniatura):
            self.assertEqual(self.client.post(url).status_code, 405, url)

    def test_una_noticia_que_no_existe_da_404(self):
        self.assertEqual(self.client.get(reverse('noticia', args=['no-existe'])).status_code, 404)


class NoticiasEnElMenuTests(TestCase):
    def test_noticias_esta_en_el_menu_principal_el_movil_y_el_pie(self):
        html = self.client.get(reverse('sobre')).content.decode()
        url = reverse('noticias')
        menu = re.search(r'<nav class="site-nav".*?</nav>', html, re.S).group(0)
        movil = re.search(r'<nav[^>]*aria-label="Menú móvil".*?</nav>', html, re.S).group(0)
        pie = re.search(r'<footer class="site-footer">.*?</footer>', html, re.S).group(0)
        for nombre, bloque in (('menú', menu), ('menú móvil', movil), ('pie', pie)):
            with self.subTest(donde=nombre):
                self.assertIn(f'<a href="{url}">Noticias</a>', bloque)
                # Mismo orden en los tres: después de Multimedia.
                self.assertLess(bloque.index('>Multimedia<'), bloque.index('>Noticias<'))

    def test_ningun_nombre_del_menu_se_parte_en_dos_lineas(self):
        # "Sobre la LMVE" se partía al sumar Noticias: no había espacio.
        html = self.client.get(reverse('home')).content.decode()
        regla = re.search(r'\n        \.site-nav a \{(.*?)\}', html, re.S).group(1)
        self.assertIn('white-space: nowrap;', regla)


class NoticiasEnLaPortadaTests(TestCase):
    def test_sin_noticias_la_portada_no_tiene_la_seccion_ni_su_css(self):
        crear_noticia(titulo='Borrador', publicada=False)
        html = self.client.get(reverse('home')).content.decode()
        self.assertNotIn('noticias-home', html)
        self.assertNotIn('noticia-card', html)

    def test_muestra_las_tres_mas_recientes_y_el_enlace_a_todas(self):
        for i in range(4):
            crear_noticia(titulo=f'Noticia número {i}', fecha=date(2026, 6, 1 + i))
        html = self.client.get(reverse('home')).content.decode()
        self.assertEqual(html.count('class="noticia-card"'), 3)
        self.assertNotIn('Noticia número 0', html)   # la más vieja queda fuera
        self.assertIn(f'href="{reverse("noticias")}"', html)

    def test_la_tarjeta_enlaza_a_la_noticia_y_usa_la_miniatura_con_medidas(self):
        noticia = crear_noticia(fotos=2)
        foto = noticia.fotos.first()
        html = self.client.get(reverse('home')).content.decode()
        tarjeta = re.search(r'<a class="noticia-card".*?</a>', html, re.S).group(0)
        self.assertIn(f'href="{noticia.get_absolute_url()}"', tarjeta)
        self.assertRegex(tarjeta, rf'<img src="{re.escape(foto.url_miniatura)}"[^>]*width="\d+" height="\d+"')
        self.assertNotIn(foto.url_grande, tarjeta)

    def test_una_noticia_sin_foto_muestra_el_logo(self):
        crear_noticia()
        self.assertContains(self.client.get(reverse('home')), 'noticia-card-foto--logo')

    def test_la_portada_no_hace_una_consulta_por_cada_noticia(self):
        for i in range(3):
            crear_noticia(titulo=f'Noticia {i}', fotos=2)
        # Una consulta para las noticias y una para todas sus fotos.
        with self.assertNumQueries(2):
            self.client.get(reverse('home'))


@override_settings(SITE_URL='https://ligamve.cl')
class NoticiasSeoTests(TestCase):
    def test_la_noticia_tiene_sus_propios_metadatos(self):
        noticia = crear_noticia(resumen='La cuarta versión fue un éxito.')
        r = self.client.get(noticia.get_absolute_url())
        self.assertContains(r, '<title>Éxito de la Copa Milled | LMVE</title>')
        self.assertContains(r, '<meta name="description" content="La cuarta versión fue un éxito.">')
        self.assertContains(r, f'<link rel="canonical" href="https://ligamve.cl{noticia.get_absolute_url()}">')
        self.assertNotContains(r, 'noindex')

    def test_sin_fotos_la_vista_previa_es_la_imagen_del_sitio(self):
        r = self.client.get(crear_noticia().get_absolute_url())
        self.assertContains(r, 'impacto-banner-sponsor')
        self.assertContains(r, 'property="og:image:width" content="1400"')

    def test_con_fotos_la_vista_previa_es_un_jpg_de_la_noticia(self):
        noticia = crear_noticia(fotos=1)
        noticia.imagen_social = imagen_social(noticia.fotos.values_list('grande', flat=True).get())
        noticia.save()
        url = reverse('noticia_social', args=[noticia.slug])
        r = self.client.get(noticia.get_absolute_url())
        self.assertContains(r, f'property="og:image" content="https://ligamve.cl{url}"')
        self.assertContains(r, 'property="og:image:width" content="1200"')
        self.assertContains(r, 'property="og:image:height" content="630"')
        imagen = self.client.get(url)
        self.assertEqual(imagen['Content-Type'], 'image/jpeg')
        self.assertEqual(Image.open(io.BytesIO(imagen.content)).size, (1200, 630))

    def test_la_vista_previa_de_un_borrador_no_es_publica(self):
        noticia = crear_noticia(publicada=False, fotos=1)
        noticia.imagen_social = imagen_social(noticia.fotos.values_list('grande', flat=True).get())
        noticia.save()
        self.assertEqual(self.client.get(reverse('noticia_social', args=[noticia.slug])).status_code, 404)

    def test_jsonld_de_la_noticia(self):
        noticia = crear_noticia(fotos=1)
        html = self.client.get(noticia.get_absolute_url()).content.decode()
        datos = json.loads(re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', html, re.S).group(1))
        self.assertEqual(datos['@type'], 'NewsArticle')
        self.assertEqual(datos['headline'], 'Éxito de la Copa Milled')
        self.assertEqual(datos['datePublished'], '2026-11-11')
        self.assertEqual(datos['image'], ['https://ligamve.cl' + noticia.fotos.get().url_grande])

    def test_el_sitemap_lista_las_publicadas_y_no_los_borradores(self):
        publicada = crear_noticia(titulo='Publicada')
        borrador = crear_noticia(titulo='Borrador', publicada=False)
        xml = self.client.get('/sitemap.xml').content.decode()
        self.assertIn(f'<loc>https://ligamve.cl{publicada.get_absolute_url()}</loc>', xml)
        self.assertNotIn(borrador.get_absolute_url(), xml)
        self.assertIn('<loc>https://ligamve.cl/noticias/</loc>', xml)


class NoticiasAdminTests(TestCase):
    def _form(self, archivo=None, instancia=None, **datos):
        datos = {'alt': 'Premiación de la Copa Milled', 'orden': 0, **datos}
        return FotoNoticiaForm(datos, {'archivo': archivo} if archivo else {}, instance=instancia)

    def test_subir_una_foto_la_guarda_procesada(self):
        noticia = crear_noticia()
        form = self._form(foto_de_celular())
        self.assertTrue(form.is_valid(), form.errors)
        foto = form.save(commit=False)
        foto.noticia = noticia
        foto.save()
        guardada = FotoNoticia.objects.values('grande', 'miniatura', 'ancho', 'version').get()
        self.assertEqual(guardada['ancho'], GRANDE)
        self.assertEqual(len(guardada['version']), 12)
        self.assertEqual(Image.open(io.BytesIO(bytes(guardada['grande']))).format, 'WEBP')
        self.assertNotIn(b'MarcaDePrueba', bytes(guardada['grande']))

    def test_una_foto_nueva_exige_archivo_y_descripcion(self):
        form = self._form()
        self.assertFalse(form.is_valid())
        self.assertIn('Falta elegir la foto.', form.errors['archivo'])
        form = self._form(foto_de_celular(), alt='')
        self.assertFalse(form.is_valid())
        self.assertIn('alt', form.errors)

    def test_un_archivo_que_no_es_foto_muestra_un_error_claro(self):
        form = self._form(SimpleUploadedFile('virus.jpg', b'MZ\x90\x00 no soy una foto'))
        self.assertFalse(form.is_valid())
        self.assertIn('no es una foto', form.errors['archivo'][0])

    def test_editar_la_descripcion_no_obliga_a_subir_la_foto_de_nuevo(self):
        foto = crear_noticia(fotos=1).fotos.get()
        version = foto.version
        form = self._form(instancia=foto, alt='Nueva descripción')
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        foto = FotoNoticia.objects.get()
        self.assertEqual(foto.alt, 'Nueva descripción')
        self.assertEqual(foto.version, version)

    def test_cambiar_la_foto_cambia_su_direccion(self):
        foto = crear_noticia(fotos=1).fotos.get()
        url = foto.url_miniatura
        form = self._form(foto_de_celular(900, 900), instancia=foto)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.assertNotEqual(FotoNoticia.objects.get().url_miniatura, url)
        self.assertEqual(self.client.get(url).status_code, 404)

    def _entrar_al_panel(self):
        """Sesión de admin con el 2FA ya verificado (el flujo del código
        por correo tiene sus propios tests en core/tests.py)."""
        usuario = User.objects.create_superuser('jefa', 'jefa@example.com', 'x')
        dispositivo = EmailDevice.objects.create(user=usuario, name='default', confirmed=True)
        self.client.force_login(usuario)
        sesion = self.client.session
        sesion[DEVICE_ID_SESSION_KEY] = dispositivo.persistent_id
        sesion.save()

    def _datos_del_formulario(self, **extra):
        datos = {
            'titulo': 'Éxito de la Copa Milled', 'fecha': '11/11/2026',
            'resumen': 'La cuarta versión fue un éxito.', 'cuerpo': 'Texto.', 'publicada': 'on',
            'fotos-TOTAL_FORMS': '1', 'fotos-INITIAL_FORMS': '0',
            'fotos-MIN_NUM_FORMS': '0', 'fotos-MAX_NUM_FORMS': '8',
            'fotos-0-alt': 'Premiación', 'fotos-0-orden': '0',
        }
        datos.update(extra)
        return datos

    def test_publicar_una_noticia_con_foto_desde_el_panel(self):
        self._entrar_al_panel()
        r = self.client.post(
            reverse('admin:core_noticia_add'),
            self._datos_del_formulario(**{'fotos-0-archivo': foto_de_celular()}),
        )
        self.assertEqual(r.status_code, 302)
        noticia = Noticia.objects.get()
        self.assertEqual(noticia.slug, 'exito-de-la-copa-milled')
        self.assertEqual(noticia.fotos.count(), 1)
        # Quedó publicada, con su foto y con la imagen para compartir.
        pagina = self.client.get(noticia.get_absolute_url())
        self.assertContains(pagina, noticia.fotos.get().url_grande)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('noticia_social', args=[noticia.slug])).status_code, 200)
        self.assertContains(self.client.get(reverse('home')), 'Éxito de la Copa Milled')

    def test_una_noticia_nueva_parte_firmada_por_quien_la_escribe(self):
        self._entrar_al_panel()
        User.objects.filter(username='jefa').update(first_name='Camila', last_name='Busch')
        r = self.client.get(reverse('admin:core_noticia_add'))
        self.assertContains(r, 'name="autor" value="Camila Busch"')
        # Y se guarda lo que diga el campo, que se puede cambiar o vaciar.
        self.client.post(reverse('admin:core_noticia_add'), self._datos_del_formulario(
            autor='Comunicaciones LMVE', **{'fotos-TOTAL_FORMS': '0'}))
        self.assertEqual(Noticia.objects.get().autor, 'Comunicaciones LMVE')

    def test_el_panel_rechaza_un_archivo_que_no_es_foto_sin_guardar_nada(self):
        self._entrar_al_panel()
        r = self.client.post(
            reverse('admin:core_noticia_add'),
            self._datos_del_formulario(**{'fotos-0-archivo': SimpleUploadedFile('x.jpg', b'<script>alert(1)</script>')}),
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no es una foto')
        self.assertEqual(Noticia.objects.count(), 0)

    def test_sin_entrar_al_panel_no_se_puede_publicar(self):
        r = self.client.post(reverse('admin:core_noticia_add'), self._datos_del_formulario())
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])
        self.assertEqual(Noticia.objects.count(), 0)

    def test_noticias_esta_en_el_admin_con_tope_de_fotos(self):
        modelo_admin = site._registry[Noticia]
        self.assertIsInstance(modelo_admin, NoticiaAdmin)
        self.assertEqual(modelo_admin.inlines[0].max_num, 8)

    def test_el_formulario_trae_la_guia_de_escritura_con_ejemplos(self):
        self._entrar_al_panel()
        r = self.client.get(reverse('admin:core_noticia_add'))
        html = r.content.decode()
        # Las tres partes de la noticia y cada tipo de línea del texto,
        # con lo que se escribe y cómo se ve.
        for texto in (
            'Cómo se arma una noticia',
            'Casilla «Título»', 'Casilla «Resumen»', 'Casilla «Texto de la noticia»',
            'con una barra naranja',
            '<pre># Cuadro de Honor</pre>', '<div class="guia-v-subtitulo">Cuadro de Honor</div>',
            '- Trofeos Milled', '1. Colegio Andrée',
            'pega el enlace solo en una línea', 'Ver en TikTok',
            'Guardar y continuar editando',
        ):
            with self.subTest(texto=texto):
                self.assertIn(texto, html)
        # Sus estilos vienen de un archivo: la CSP bloquea los estilos en
        # línea, y la guía no puede depender de ellos.
        self.assertRegex(html, r'<link href="/static/core/css/admin-noticias\.[0-9a-f]+\.css"')
        guia = html[html.index('<div class="guia">'):html.index('Antes de publicar')]
        self.assertNotIn('style=', guia)
        # El slug y las imágenes procesadas no se editan a mano.
        campos = [c for _, opciones in site._registry[Noticia].get_fieldsets(r.wsgi_request)
                  for c in opciones['fields']]
        self.assertEqual(campos, ['titulo', 'fecha', 'autor', 'resumen', 'cuerpo', 'publicada'])

    def test_los_ejemplos_de_la_guia_son_los_que_de_verdad_produce_el_sitio(self):
        # Si la guía promete que "# Cuadro de Honor" es un subtítulo o
        # que un guion hace una lista, el sitio tiene que cumplirlo.
        html = cuerpo_noticia(
            'El torneo fue un éxito.\n\nGracias a todos los colegios.\n\n# Cuadro de Honor\n\n'
            '- Trofeos Milled\n- Balones Molten\n\n1. Colegio Andrée\n2. Liceo Alianza Francesa\n\n'
            'https://www.youtube.com/watch?v=abc123XYZ00\n\nhttps://www.tiktok.com/@liga/video/123456\n\n'
            'Escríbenos en https://ligamve.cl/contacto/ para inscribirte.'
        )
        self.assertIn('<p>El torneo fue un éxito.</p>\n<p>Gracias a todos los colegios.</p>', html)
        self.assertIn('<h2>Cuadro de Honor</h2>', html)
        self.assertIn('<ul><li>Trofeos Milled</li><li>Balones Molten</li></ul>', html)
        self.assertIn('<ol><li>Colegio Andrée</li><li>Liceo Alianza Francesa</li></ol>', html)
        self.assertIn('youtube-nocookie.com/embed/abc123XYZ00', html)
        self.assertIn('>Ver en TikTok</a>', html)
        self.assertIn('<a href="https://ligamve.cl/contacto/"', html)
