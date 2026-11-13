import io
import re
import zipfile
from datetime import timedelta
from unittest import mock

from django.apps import apps as django_apps
from django.test import TestCase
from django.utils import timezone

from main.apps.accounts.models import User, UserPreferences
from main.apps.analysis.engine import analyze
from main.apps.editor.exporters import DocumentExporter, _blocked_url_fetcher
from main.apps.editor.models import Document, DocumentVersion
from main.apps.notes.models import Note, NoteLink, Tag
from main.apps.notes.utils import parse_wiki_links
from main.apps.projects.models import Project, Task
from main.utils import clean_html, count_words


class UtilsTests(TestCase):
    def test_clean_html_removes_scripts_handlers_and_js_urls(self):
        dirty = ('<p onclick="x()">hola</p><script>alert(1)</script>'
                 '<a href="javascript:alert(1)">l</a><img src=x onerror=alert(1)>'
                 '<a href="https://ok.example" target="_blank">ok</a>')
        out = clean_html(dirty)
        for bad in ('<script', 'onclick', 'onerror', 'javascript:'):
            self.assertNotIn(bad, out)
        self.assertIn('https://ok.example', out)
        self.assertIn('<p>hola</p>', out)

    def test_clean_html_keeps_quill_markup(self):
        html = '<h1>T</h1><p class="ql-align-center"><strong>a</strong> <em>b</em></p><ul><li>x</li></ul><pre class="ql-syntax" spellcheck="false">c</pre>'
        self.assertEqual(clean_html(html), html)

    def test_count_words_handles_entities_and_inline_tags(self):
        self.assertEqual(count_words('<p>Hola&nbsp;mundo</p>'), 2)
        self.assertEqual(count_words('<p><strong>Ho</strong>la mundo &amp; más</p>'), 4)


class AnalysisTests(TestCase):
    def test_active_sentences_are_not_passive(self):
        self.assertEqual(analyze('<p>La casa es bonita y la mesa es grande.</p>')['passive_voice_count'], 0)

    def test_real_passive_is_detected(self):
        self.assertEqual(analyze('<p>El libro fue escrito por ella. La carta fue enviada ayer.</p>')['passive_voice_count'], 2)

    def test_paragraphs_counted_from_html_blocks(self):
        self.assertEqual(analyze('<p>Uno.</p><p>Dos.</p><h2>Tres</h2>')['paragraph_count'], 3)

    def test_nbsp_is_not_a_word(self):
        self.assertEqual(analyze('<p>a&nbsp;b</p>')['word_count'], 2)


class AccountTests(TestCase):
    def test_register_works_with_custom_user_model(self):
        r = self.client.post('/accounts/register/', {
            'username': 'ana', 'password1': 'Xk39!zzqq77', 'password2': 'Xk39!zzqq77'})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(UserPreferences.objects.filter(user__username='ana').exists())

    def test_profile_survives_invalid_numbers(self):
        u = User.objects.create_user('bob', password='x')
        self.client.force_login(u)
        r = self.client.post('/accounts/profile/', {
            'editor_font_size': 'abc', 'theme': 'neon', 'autosave_interval': '99999'})
        self.assertEqual(r.status_code, 302)
        prefs = UserPreferences.objects.get(user=u)
        self.assertEqual(prefs.editor_font_size, 17)
        self.assertEqual(prefs.theme, 'dark')
        self.assertEqual(prefs.autosave_interval, 600)


class EditorTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user('bob', password='x')
        self.client.force_login(self.u)
        self.doc = Document.objects.create(
            owner=self.u, title='Mi "doc" ñ',
            content='<p>Hola <strong>mundo</strong> y&nbsp;más</p><ul><li>uno</li><li>dos</li></ul><blockquote>cita</blockquote><p>fin</p>')

    def test_autosave_sanitizes_content(self):
        r = self.client.post(f'/editor/{self.doc.pk}/autosave/',
                             data={'title': 'x', 'content': '<p>ok</p><script>alert(1)</script>'},
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.content, '<p>ok</p>alert(1)')
        self.assertNotIn('<script', self.doc.content)

    def test_autosave_bad_json_is_400_not_500(self):
        r = self.client.post(f'/editor/{self.doc.pk}/autosave/', data='{no', content_type='application/json')
        self.assertEqual(r.status_code, 400)

    def test_snapshot_is_time_based_and_skips_unchanged(self):
        url = f'/editor/{self.doc.pk}/autosave/'
        post = lambda c: self.client.post(url, data={'title': 't', 'content': c}, content_type='application/json')
        post('<p>uno</p>')
        self.assertEqual(self.doc.versions.count(), 1)
        post('<p>dos</p>')                      # < 30 min: sin nueva versión
        self.assertEqual(self.doc.versions.count(), 1)
        DocumentVersion.objects.filter(document=self.doc).update(created_at=timezone.now() - timedelta(hours=1))
        post('<p>dos</p>')                      # > 30 min y cambió
        self.assertEqual(self.doc.versions.count(), 2)

    def test_restore_requires_post_and_keeps_current_as_version(self):
        v = DocumentVersion.objects.create(document=self.doc, content='<p>vieja</p>', word_count=1)
        url = f'/editor/{self.doc.pk}/versions/{v.pk}/restore/'
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.content, '<p>vieja</p>')
        self.assertEqual(self.doc.versions.count(), 2)

    def test_unknown_export_format_is_404(self):
        self.assertEqual(self.client.get(f'/editor/{self.doc.pk}/export/zzz/').status_code, 404)

    def test_export_formats_and_filename(self):
        for fmt, ctype in (('markdown', 'text/markdown'), ('html', 'text/html'), ('txt', 'text/plain'),
                           ('odt', 'application/vnd.oasis.opendocument.text')):
            r = self.client.get(f'/editor/{self.doc.pk}/export/{fmt}/')
            self.assertEqual(r.status_code, 200, fmt)
            self.assertEqual(r['Content-Type'].split(';')[0], ctype)
            self.assertIn('attachment', r['Content-Disposition'])
            self.assertNotIn('\n', r['Content-Disposition'])

    def test_html_export_is_sanitized(self):
        Document.objects.filter(pk=self.doc.pk).update(content='<p>x</p><script>alert(1)</script><img src=x onerror=alert(1)>')
        body = self.client.get(f'/editor/{self.doc.pk}/export/html/').content.decode()
        self.assertNotIn('<script>alert', body)
        self.assertNotIn('onerror', body)

    def test_odt_keeps_lists_quotes_and_inline_spacing(self):
        r = self.client.get(f'/editor/{self.doc.pk}/export/odt/')
        xml = zipfile.ZipFile(io.BytesIO(r.content)).read('content.xml').decode()
        text = re.sub(r'<[^>]+>', '', xml)
        for expected in ('Hola mundo', 'uno', 'dos', 'cita', 'fin'):
            self.assertIn(expected, text)

    def test_pdf_blocks_external_resources(self):
        with self.assertRaises(ValueError):
            _blocked_url_fetcher('file:///etc/passwd')
        with self.assertRaises(ValueError):
            _blocked_url_fetcher('http://169.254.169.254/')
        r = self.client.get(f'/editor/{self.doc.pk}/export/pdf/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')

    def test_editor_page_escapes_title_without_escapejs_artifacts(self):
        Document.objects.filter(pk=self.doc.pk).update(title="Don't <b>")
        body = self.client.get(f'/editor/{self.doc.pk}/').content.decode()
        self.assertNotIn('\\u0027', body)
        self.assertIn('value="Don&#x27;t &lt;b&gt;"', body)


class NotesTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user('bob', password='x')
        self.other = User.objects.create_user('eve', password='x')
        self.client.force_login(self.u)

    def test_wiki_links_escape_html_and_encode_urls(self):
        out = parse_wiki_links('hola <img src=x onerror=alert(1)> [[A "b" & <i>]]', self.u)
        self.assertNotIn('<img', out)
        self.assertNotIn('<i>', out)
        self.assertIn('wiki-link--new', out)
        self.assertIn('title=A+%22b%22+%26+%3Ci%3E', out)

    def test_wiki_link_resolves_accented_titles_and_paragraphs(self):
        target = Note.objects.create(owner=self.u, title='Ñandú')
        out = parse_wiki_links('uno\n\ndos [[Ñandú]]\ntres', self.u)
        self.assertIn(f'href="/notes/{target.slug}/"', out)
        self.assertEqual(out.count('<p>'), 2)
        self.assertIn('<br>', out)

    def test_sync_links_creates_backlinks(self):
        a = Note.objects.create(owner=self.u, title='Alfa')
        Note.objects.create(owner=self.u, title='Beta')
        self.client.post(f'/notes/{a.slug}/save/', data={'title': 'Alfa', 'content': 'ver [[Beta]] y [[beta]]', 'tags': []},
                         content_type='application/json')
        self.assertEqual(NoteLink.objects.filter(from_note=a).count(), 1)

    def test_tags_are_per_user(self):
        mine = Note.objects.create(owner=self.u, title='m')
        theirs = Note.objects.create(owner=self.other, title='t')
        self.client.post(f'/notes/{mine.slug}/save/', data={'title': 'm', 'content': '', 'tags': ['  x ', 'x', '', "o'brien"]},
                         content_type='application/json')
        self.assertEqual(sorted(mine.tags.values_list('name', flat=True)), ["o'brien", 'x'])
        self.assertEqual(Tag.objects.filter(owner=self.u).count(), 2)
        Tag.objects.create(owner=self.other, name='secreto')
        body = self.client.get(f'/notes/{mine.slug}/edit/').content.decode()
        self.assertNotIn('secreto', body)
        self.assertNotIn('secreto', self.client.get('/notes/').content.decode())

    def test_graph_and_edit_pages_do_not_break_out_of_script(self):
        n = Note.objects.create(owner=self.u, title='</script><script>alert(1)</script>')
        self.assertNotIn('</script><script>alert(1)',
                         self.client.get('/notes/graph/').content.decode())
        t = Tag.objects.create(owner=self.u, name="</script><b>")
        n.tags.add(t)
        self.assertNotIn('</script><b>', self.client.get(f'/notes/{n.slug}/edit/').content.decode())

    def test_note_page_shows_text_escaped_with_line_breaks(self):
        n = Note.objects.create(owner=self.u, title='n', content='a <script>alert(1)</script>\n\nb')
        body = self.client.get(f'/notes/{n.slug}/').content.decode()
        self.assertNotIn('<script>alert(1)', body)
        self.assertIn('&lt;script&gt;', body)
        self.assertEqual(n.word_count(), 3)   # texto plano: split por espacios

    def test_long_title_from_query_string_does_not_crash(self):
        r = self.client.get('/notes/new/?title=' + 'x' * 600)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(Note.objects.get(owner=self.u).title), 255)


class ProjectTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user('bob', password='x')
        self.client.force_login(self.u)
        self.p = Project.objects.create(owner=self.u, name='P')

    def test_project_create_defaults_and_color_validation(self):
        self.client.post('/projects/new/', {'name': '', 'cover_color': 'red;x'})
        p = Project.objects.exclude(pk=self.p.pk).get()
        self.assertEqual((p.name, p.cover_color), ('Nuevo proyecto', '#6366f1'))

    def test_task_status_validated(self):
        t = Task.objects.create(project=self.p, title='t')
        r = self.client.post(f'/projects/{self.p.pk}/tasks/{t.pk}/move/', data={'status': 'hack'}, content_type='application/json')
        self.assertEqual(r.status_code, 400)
        r = self.client.post(f'/projects/{self.p.pk}/tasks/{t.pk}/move/', data={'status': 'done'}, content_type='application/json')
        self.assertEqual(r.status_code, 200)

    def test_section_autosave_sanitizes_and_counts_words(self):
        s = self.p.sections.create(title='s')
        r = self.client.post(f'/projects/{self.p.pk}/sections/{s.pk}/save/',
                             data={'title': 'T' * 400, 'content': '<p>a&nbsp;b</p><script>x</script>'},
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        s.refresh_from_db()
        self.assertNotIn('<script', s.content)
        self.assertEqual(len(s.title), 255)
        self.assertEqual(s.word_count, 3)   # "a", "b" y "x" (texto del script ya sin etiqueta)

    def test_event_with_garbage_ids_does_not_crash(self):
        r = self.client.post(f'/projects/{self.p.pk}/events/new/',
                             data={'title': 'e', 'character_ids': 'nope', 'place_ids': [1, 'x', None]},
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)


class SearchTests(TestCase):
    def test_palette_skips_archived(self):
        u = User.objects.create_user('bob', password='x')
        self.client.force_login(u)
        Document.objects.create(owner=u, title='visible')
        Document.objects.create(owner=u, title='visible oculto', is_archived=True)
        results = self.client.get('/search/palette/?q=visible').json()['results']
        self.assertEqual([r['title'] for r in results], ['visible'])


# ── Páginas (tamaño de página, editor paginado, exportación) ─────────────────
import shutil
import subprocess
import unittest
from pathlib import Path

from main.apps.editor.pagesizes import DEFAULT_PAGE_SIZE, PAGE_SIZES, get_page, mm


class PageSizeTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user('bob', password='x')
        self.client.force_login(self.u)
        self.doc = Document.objects.create(
            owner=self.u, title='Libro',
            content='<h1>Cap</h1><p>Hola <strong>mundo</strong></p><ul><li>uno</li></ul>')

    def autosave(self, **data):
        data.setdefault('title', 'Libro')
        return self.client.post(f'/editor/{self.doc.pk}/autosave/', data=data,
                                content_type='application/json')

    def test_default_is_a5_and_catalogue_is_valid(self):
        self.assertEqual(DEFAULT_PAGE_SIZE, 'A5')
        self.assertEqual(self.doc.page_size, 'A5')
        for key in ('A3', 'A4', 'A5', 'A6', 'LETTER', 'LEGAL'):
            self.assertIn(key, PAGE_SIZES)
        for page in PAGE_SIZES.values():
            self.assertGreater(page['w'] - 2 * page['margin'], 50)
            self.assertGreater(page['h'] - 2 * page['margin'], 80)
        self.assertEqual(get_page('nope')['key'], 'A5')
        self.assertEqual(mm(215.9), '215.9')

    def test_editor_shows_selector_with_a5_selected_and_pagination_script(self):
        body = self.client.get(f'/editor/{self.doc.pk}/').content.decode()
        self.assertIn('id="page-size-select"', body)
        self.assertRegex(body, r'<option value="A5" selected>')
        for key in ('A3', 'A4', 'A6', 'LETTER'):
            self.assertIn(f'<option value="{key}"', body)
        self.assertIn('/static/js/pagination.js', body)
        self.assertIn('id="pg-cur"', body)

    def test_autosave_stores_valid_page_size_and_ignores_invalid(self):
        r = self.autosave(content='<p>x</p>', page_size='A3')
        self.assertEqual(r.json()['page_size'], 'A3')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.page_size, 'A3')
        self.autosave(content='<p>x</p>', page_size='../../etc')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.page_size, 'A3')

    def test_pagination_markup_from_the_client_is_not_persisted(self):
        self.autosave(content='<p data-pg="1" style="margin-top: 312px">x</p>')
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.content, '<p>x</p>')

    def test_html_export_uses_the_documents_page_size(self):
        for key, size in (('A4', '210mm 297mm'), ('A5', '148mm 210mm'),
                          ('A3', '297mm 420mm'), ('LETTER', '215.9mm 279.4mm')):
            Document.objects.filter(pk=self.doc.pk).update(page_size=key)
            body = self.client.get(f'/editor/{self.doc.pk}/export/html/').content.decode()
            self.assertIn(f'size: {size};', body, key)
            self.assertIn(f'margin: {PAGE_SIZES[key]["margin"]}mm;', body)
            self.assertNotRegex(body, r'size: [\d]+,[\d]')       # nunca coma decimal
        self.assertIn('id="doc-root"', body)
        self.assertIn('WritaraPages', body)                       # vista en hojas incluida

    def test_export_uses_user_typography(self):
        UserPreferences.objects.update_or_create(
            user=self.u, defaults={'editor_font_size': 20, 'paragraph_spacing': 6, 'text_indent': 12})
        body = self.client.get(f'/editor/{self.doc.pk}/export/html/').content.decode()
        self.assertIn('font-size: 20px;', body)
        self.assertIn('margin: 0 0 6px; text-indent: 12px;', body)

    def test_pdf_receives_page_rules(self):
        Document.objects.filter(pk=self.doc.pk).update(page_size='A4')
        with mock.patch('weasyprint.HTML') as fake_html:
            fake_html.return_value.write_pdf.return_value = b'%PDF-1.7'
            r = self.client.get(f'/editor/{self.doc.pk}/export/pdf/')
        self.assertEqual(r.status_code, 200)
        html = fake_html.call_args.kwargs['string']
        self.assertIn('size: 210mm 297mm;', html)
        self.assertIn('counter(page)', html)
        self.assertIn('url_fetcher', fake_html.call_args.kwargs)

    def test_odt_has_page_layout_and_page_numbers(self):
        for key in ('A5', 'A4', 'LETTER'):
            Document.objects.filter(pk=self.doc.pk).update(page_size=key)
            r = self.client.get(f'/editor/{self.doc.pk}/export/odt/')
            archive = zipfile.ZipFile(io.BytesIO(r.content))
            styles = archive.read('styles.xml').decode() + archive.read('content.xml').decode()
            page = PAGE_SIZES[key]
            self.assertIn(f'fo:page-width="{mm(page["w"])}mm"', styles, key)
            self.assertIn(f'fo:page-height="{mm(page["h"])}mm"', styles, key)
            self.assertIn(f'fo:margin-left="{mm(page["margin"])}mm"', styles)
            self.assertIn('text:page-number', styles)
            self.assertIn('style:name="Standard"', styles)

    @unittest.skipUnless(shutil.which('soffice'), 'LibreOffice no disponible')
    def test_odt_converts_to_multiple_pages_of_the_chosen_size(self):
        import tempfile
        long_text = ''.join(f'<p>Párrafo {i}. ' + 'palabra ' * 60 + '</p>' for i in range(40))
        Document.objects.filter(pk=self.doc.pk).update(content=long_text, page_size='A5')
        odt = self.client.get(f'/editor/{self.doc.pk}/export/odt/').content
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'doc.odt'
            path.write_bytes(odt)
            subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', tmp, str(path)],
                           check=True, capture_output=True, timeout=180,
                           env={**__import__('os').environ, 'HOME': tmp})
            info = subprocess.run(['pdfinfo', str(Path(tmp) / 'doc.pdf')],
                                  capture_output=True, text=True, check=True).stdout
        pages = int(re.search(r'Pages:\s+(\d+)', info).group(1))
        size = re.search(r'Page size:\s+([\d.]+) x ([\d.]+) pts', info)
        self.assertGreater(pages, 3)
        self.assertAlmostEqual(float(size.group(1)) / 72 * 25.4, 148, delta=1)
        self.assertAlmostEqual(float(size.group(2)) / 72 * 25.4, 210, delta=1)

    @unittest.skipUnless(shutil.which('node'), 'Node no disponible')
    def test_pagination_algorithm_js_tests_pass(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(['node', str(root / 'tests_js' / 'pagination.test.js')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


# ── Notas: regresiones (JS roto del editor, grafo, slugs, inbox, enlaces…) ───
import tempfile

from main.apps.notes.utils import title_to_slug

JS_ROOT = Path(__file__).resolve().parents[1] / 'tests_js'


def inline_scripts(html):
    """Código de los <script> inline (sin src y sin JSON de datos)."""
    return re.findall(r'<script(?![^>]*\bsrc=)(?![^>]*type="application/json")[^>]*>(.*?)</script>', html, re.S)


@unittest.skipUnless(shutil.which('node'), 'Node no disponible')
class PageScriptTests(TestCase):
    """Un <script> mal cerrado rompe una página entera sin que Django lo note."""

    def setUp(self):
        self.u = User.objects.create_user('bob', password='x')
        self.client.force_login(self.u)
        self.note = Note.objects.create(owner=self.u, title='Alfa', content='ver [[Beta]]')
        self.note.tags.add(Tag.objects.create(owner=self.u, name="o'brien"),
                           Tag.objects.create(owner=self.u, name='</script>x'))
        self.doc = Document.objects.create(owner=self.u, title='Doc', content='<p>x</p>')
        self.project = Project.objects.create(owner=self.u, name='P')
        self.section = self.project.sections.create(title='S')

    def node_check(self, code):
        with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False, encoding='utf-8') as f:
            f.write(code)
        return subprocess.run(['node', '--check', f.name], capture_output=True, text=True)

    def test_every_page_renders_with_valid_inline_javascript(self):
        urls = ['/notes/', f'/notes/{self.note.slug}/', f'/notes/{self.note.slug}/edit/', '/notes/graph/',
                '/editor/', f'/editor/{self.doc.pk}/', '/projects/', f'/projects/{self.project.pk}/',
                f'/projects/{self.project.pk}/sections/{self.section.pk}/', '/accounts/profile/',
                '/search/?q=al', f'/analysis/{self.doc.pk}/']
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            for i, code in enumerate(inline_scripts(response.content.decode())):
                result = self.node_check(code)
                self.assertEqual(result.returncode, 0, f'{url} script #{i}: {result.stderr[-300:]}')

    def test_note_editor_javascript_behaviour(self):
        html = self.client.get(f'/notes/{self.note.slug}/edit/').content.decode()
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
            f.write(html)
        result = subprocess.run(['node', str(JS_ROOT / 'note_editor.test.js'), f.name],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr[-800:])


class NoteRegressionTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user('bob', password='x')
        self.client.force_login(self.u)

    def save(self, note, **data):
        data.setdefault('title', note.title)
        data.setdefault('content', note.content)
        data.setdefault('tags', [])
        return self.client.post(f'/notes/{note.slug}/save/', data=data, content_type='application/json')

    def test_notes_titled_like_a_fixed_route_stay_reachable(self):
        for title in ('Graph', 'New', 'Quick', 'Autocomplete'):
            note = Note.objects.create(owner=self.u, title=title, content='x')
            self.assertTrue(note.slug.endswith('-nota'), note.slug)
            self.assertEqual(self.client.get(f'/notes/{note.slug}/').status_code, 200)
        self.assertEqual(title_to_slug('Graph'), 'graph-nota')
        self.assertEqual(title_to_slug('Ñandú'), 'nandu')

    def test_existing_reserved_slugs_are_fixed_by_the_migration(self):
        from importlib import import_module
        migration = import_module('main.apps.notes.migrations.0005_fix_reserved_slugs')
        broken = Note.objects.create(owner=self.u, title='x')
        Note.objects.filter(pk=broken.pk).update(slug='graph')
        migration.fix_reserved_slugs(django_apps, None)
        broken.refresh_from_db()
        self.assertEqual(broken.slug, 'graph-nota')

    def test_graph_empty_state_and_edges_ignore_inbox_notes(self):
        self.assertIn('Sin notas conectadas', self.client.get('/notes/graph/').content.decode())
        a = Note.objects.create(owner=self.u, title='A', content='[[Entrada]]')
        Note.objects.create(owner=self.u, title='Entrada', is_inbox=True)
        self.save(a)
        self.assertEqual(NoteLink.objects.count(), 1)               # existe el enlace…
        body = self.client.get('/notes/graph/').content.decode()
        self.assertNotIn('Sin notas conectadas', body)
        self.assertIn('id="graph-edges" type="application/json">[]<', body)  # …pero no se pinta (d3 fallaría)

    def test_editing_an_inbox_note_processes_it(self):
        self.client.post('/notes/quick/', data={'content': 'idea rápida'}, content_type='application/json')
        note = Note.objects.get()
        self.assertTrue(note.is_inbox)
        self.save(note, content='idea desarrollada')
        note.refresh_from_db()
        self.assertFalse(note.is_inbox)
        self.assertIn('idea desarrollada', self.client.get('/notes/').content.decode())

    def test_links_written_before_the_target_exists_connect_when_it_is_created(self):
        alfa = Note.objects.create(owner=self.u, title='Alfa', content='ver [[Beta]]')
        self.save(alfa)
        self.assertEqual(NoteLink.objects.count(), 0)
        self.client.get('/notes/new/?title=Beta')                  # clic en el enlace "Beta +"
        self.assertEqual(NoteLink.objects.filter(from_note=alfa, to_note__title='Beta').count(), 1)

    def test_links_survive_renames_and_repoint_when_another_note_takes_the_title(self):
        beta = Note.objects.create(owner=self.u, title='Beta')
        alfa = Note.objects.create(owner=self.u, title='Alfa', content='ver [[Beta]]')
        self.save(alfa)
        self.save(beta, title='Gamma')                               # la URL (slug) no cambia
        link = NoteLink.objects.get(from_note=alfa)
        self.assertEqual(link.to_note, beta)                         # [[Beta]] sigue llegando a la nota renombrada
        delta = Note.objects.create(owner=self.u, title='Delta')
        self.save(delta, title='Beta')                               # ahora otra nota se llama "Beta"…
        self.assertEqual(NoteLink.objects.get(from_note=alfa).to_note, delta)   # …y el enlace se reasigna solo

    def test_new_note_link_reuses_existing_note_instead_of_duplicating(self):
        beta = Note.objects.create(owner=self.u, title='Beta')
        response = self.client.get('/notes/new/?title=beta')
        self.assertRedirects(response, f'/notes/{beta.slug}/edit/', fetch_redirect_response=False)
        self.assertEqual(Note.objects.count(), 1)
        self.client.get('/notes/new/')
        self.client.get('/notes/new/')
        self.assertEqual(Note.objects.count(), 3)                   # sin título sí crea una nueva cada vez

    def test_tag_filter_links_are_url_encoded(self):
        note = Note.objects.create(owner=self.u, title='n')
        self.save(note, tags=['c++ & más'])
        body = self.client.get('/notes/').content.decode()
        self.assertIn('/notes/?tag=c%2B%2B%20%26%20m%C3%A1s"', body)
        filtered = self.client.get('/notes/?tag=c%2B%2B%20%26%20m%C3%A1s').content.decode()
        self.assertIn('>n<', filtered)

    def test_previews_show_plain_text_not_stripped(self):
        Note.objects.create(owner=self.u, title='m', content='si a<b y c>d entonces')
        body = self.client.get('/notes/').content.decode()
        self.assertIn('si a&lt;b y c&gt;d entonces', body)

    def test_textarea_keeps_a_leading_blank_line(self):
        note = Note.objects.create(owner=self.u, title='n', content='\nhola')
        self.assertIn('>\n\nhola</textarea>', self.client.get(f'/notes/{note.slug}/edit/').content.decode())

    def test_quick_capture_reports_failures_instead_of_pretending(self):
        body = self.client.get('/notes/').content.decode()
        self.assertIn('if (!r.ok) throw', body)

    def test_other_users_cannot_touch_my_notes(self):
        mine = Note.objects.create(owner=self.u, title='privada', content='secreto')
        eve = User.objects.create_user('eve', password='x')
        self.client.force_login(eve)
        self.assertEqual(self.client.get(f'/notes/{mine.slug}/').status_code, 404)
        self.assertEqual(self.save(mine, content='hack').status_code, 404)
        self.assertNotIn('privada', self.client.get('/notes/graph/').content.decode())
