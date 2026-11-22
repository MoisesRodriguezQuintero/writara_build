"""Pruebas en un navegador real (Chromium vía Playwright) del guardado de notas.

Se saltan solas si Playwright o Chromium no están instalados. Detectan lo que las
pruebas con el cliente de Django no pueden ver: scripts mal cerrados, funciones
sin definir, CSRF real, eventos del teclado y guardado al salir de la página."""
import os
import re
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from main.apps.accounts.models import User
from main.apps.notes.models import Note

# Playwright (API síncrona) corre su propio bucle asyncio en este hilo y Django lo toma por un
# contexto async al usar el ORM en los tests; es el ajuste que Django documenta para este caso.
os.environ.setdefault('DJANGO_ALLOW_ASYNC_UNSAFE', 'true')

try:
    from playwright.sync_api import sync_playwright
except ImportError:                                   # pragma: no cover
    sync_playwright = None


@unittest.skipUnless(sync_playwright, 'Playwright no instalado')
class BrowserTestBase(StaticLiveServerTestCase):
    """Navegador compartido, usuario con sesión iniciada y utilidades."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._pw = sync_playwright().start()
        try:
            cls.browser = cls._pw.chromium.launch(args=['--no-sandbox'])
        except Exception as exc:                      # Chromium no descargado
            cls._pw.stop()
            super().tearDownClass()
            raise unittest.SkipTest(f'Chromium no disponible: {exc}')

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls._pw.stop()
        super().tearDownClass()

    def setUp(self):
        self.user = User.objects.create_user('bob', password='x')
        self.client.force_login(self.user)
        self.context = self.browser.new_context()
        self.context.add_cookies([{'name': 'sessionid', 'value': self.client.cookies['sessionid'].value,
                                   'url': self.live_server_url}])
        # No se intercepta la red (page.route): Playwright aborta así las peticiones `keepalive`
        # que se lanzan al descargar la página y falsearía el test de "guardar al salir".
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))

    def tearDown(self):
        self.context.close()

    def open_editor(self, note):
        self.page.goto(f'{self.live_server_url}/notes/{note.slug}/edit/')
        self.page.wait_for_load_state()
        self.assertEqual(self.errors, [], 'la página lanzó errores de JavaScript al cargar')

    def status(self):
        return self.page.inner_text('#note-status')



@unittest.skipUnless(sync_playwright, 'Playwright no instalado')
class NoteEditorBrowserTests(BrowserTestBase):

    def test_autosave_saves_after_typing(self):
        note = Note.objects.create(owner=self.user, title='Mi nota', content='inicial')
        self.open_editor(note)
        self.page.click('#note-content')
        self.page.keyboard.press('End')
        self.page.keyboard.type(' y más')
        self.assertEqual(self.status(), 'Sin guardar…')
        self.page.wait_for_function("document.getElementById('note-status').textContent.startsWith('Guardado ')",
                                    timeout=8000)
        note.refresh_from_db()
        self.assertEqual(note.content, 'inicial y más')

    def test_save_button_title_and_tags(self):
        note = Note.objects.create(owner=self.user, title='Mi nota', content='x')
        self.open_editor(note)
        self.page.fill('#note-title', 'Título nuevo')
        self.page.fill('#note-content', 'texto <b>con</b> "comillas" ñ 😀')
        self.page.fill('#tag-input', 'uno, dos')
        self.page.press('#tag-input', 'Enter')
        self.page.click('button:has-text("Guardar")')
        self.page.wait_for_function("document.getElementById('note-status').textContent.startsWith('Guardado ')")
        note.refresh_from_db()
        self.assertEqual((note.title, note.content), ('Título nuevo', 'texto <b>con</b> "comillas" ñ 😀'))
        self.assertEqual(sorted(t.name for t in note.tags.all()), ['dos', 'uno'])
        self.page.reload()
        self.assertEqual(self.page.input_value('#note-content'), 'texto <b>con</b> "comillas" ñ 😀')
        self.assertEqual(self.page.locator('#tags-display .tag').count(), 2)

    def test_leaving_the_page_quickly_does_not_lose_text(self):
        note = Note.objects.create(owner=self.user, title='Mi nota', content='x')
        self.open_editor(note)
        self.page.fill('#note-content', 'escrito justo antes de salir')
        self.page.click('a:has-text("Ver")')                       # antes de los 3 s del autoguardado
        self.page.wait_for_url(re.compile(rf'/notes/{note.slug}/$'))
        note.refresh_from_db()
        self.assertEqual(note.content, 'escrito justo antes de salir')
        # y la página que se abre ya muestra el texto nuevo (no el anterior)
        self.assertIn('escrito justo antes de salir', self.page.inner_text('.note-content'))

    def test_following_any_link_with_pending_changes_saves_first(self):
        note = Note.objects.create(owner=self.user, title='Mi nota', content='x')
        self.open_editor(note)
        self.page.fill('#note-content', 'cambio antes de ir a proyectos')
        self.page.click('.sidebar a:has-text("Proyectos")')
        self.page.wait_for_url(re.compile(r'/projects/$'))
        note.refresh_from_db()
        self.assertEqual(note.content, 'cambio antes de ir a proyectos')

    def test_new_note_flow_from_the_list(self):
        self.page.goto(f'{self.live_server_url}/notes/')
        self.page.click('a:has-text("+ Nueva")')
        self.page.wait_for_url(re.compile(r'/notes/.+/edit/$'))
        self.page.fill('#note-title', 'Recién creada')
        self.page.fill('#note-content', 'con [[Otra]] enlace')
        self.page.click('button:has-text("Guardar")')
        self.page.wait_for_function("document.getElementById('note-status').textContent.startsWith('Guardado ')")
        note = Note.objects.get(owner=self.user)
        self.assertEqual((note.title, note.content), ('Recién creada', 'con [[Otra]] enlace'))
        self.assertEqual(self.errors, [])

    def test_failed_save_is_reported(self):
        note = Note.objects.create(owner=self.user, title='Mi nota', content='x')
        self.open_editor(note)
        note.delete()                                              # el servidor responderá 404
        self.page.fill('#note-content', 'cambio')
        self.page.click('button:has-text("Guardar")')
        self.page.wait_for_function("document.getElementById('note-status').textContent.startsWith('Error')")
        self.assertIn('404', self.status())


@unittest.skipUnless(sync_playwright, 'Playwright no instalado')
class NotesInProjectBrowserTests(BrowserTestBase):
    """La pestaña «Notas» del proyecto y el flujo crear → editar → mover, en navegador real."""

    def setUp(self):
        super().setUp()
        from main.apps.projects.models import Project
        self.novela = Project.objects.create(owner=self.user, name='Novela')
        self.ensayo = Project.objects.create(owner=self.user, name='Ensayo')

    def visible_tabs(self):
        return self.page.evaluate("[...document.querySelectorAll('.tab-content')]"
                                  ".filter(e => e.style.display !== 'none').map(e => e.id)")

    def test_url_hash_opens_the_notes_tab(self):
        Note.objects.create(owner=self.user, project=self.novela, title='Idea de trama')
        self.page.goto(f'{self.live_server_url}/projects/{self.novela.pk}/#notes')
        self.page.wait_for_load_state()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.visible_tabs(), ['tab-notes'])
        self.assertTrue(self.page.is_visible('text=Idea de trama'))
        self.page.click('button[data-tab="tasks"]')
        self.assertEqual(self.visible_tabs(), ['tab-tasks'])
        self.assertTrue(self.page.url.endswith('#tasks'))

    def test_create_note_from_the_project_edit_and_move_it(self):
        self.page.goto(f'{self.live_server_url}/projects/{self.novela.pk}/')
        self.page.click('button[data-tab="notes"]')
        self.page.click('a:has-text("+ Nueva nota")')
        self.page.wait_for_url(re.compile(r'/notes/.+/edit/$'))
        self.assertEqual(self.errors, [])
        self.assertEqual(self.page.evaluate('window.WRITARA_PROJECT_ID'), self.novela.pk)
        self.page.fill('#note-title', 'Apunte')
        self.page.fill('#note-content', 'texto del apunte')
        self.page.click('button:has-text("Guardar")')
        self.page.wait_for_function("document.getElementById('note-status').textContent.startsWith('Guardado ')")
        note = Note.objects.get(title='Apunte')
        self.assertEqual(note.project, self.novela)
        # mover a otro proyecto desde el selector
        self.page.select_option('#note-project', str(self.ensayo.pk))
        self.page.wait_for_function("document.getElementById('note-status').textContent.startsWith('Guardado ')")
        note.refresh_from_db()
        self.assertEqual(note.project, self.ensayo)
        self.assertEqual(self.page.evaluate('window.WRITARA_PROJECT_ID'), self.ensayo.pk)

    def test_back_from_a_note_returns_to_the_notes_tab(self):
        note = Note.objects.create(owner=self.user, project=self.novela, title='Apunte', content='x')
        self.page.goto(f'{self.live_server_url}/notes/{note.slug}/')
        self.page.click('a:has-text("← Novela")')
        self.page.wait_for_url(re.compile(rf'/projects/{self.novela.pk}/#notes$'))
        self.assertEqual(self.visible_tabs(), ['tab-notes'])
