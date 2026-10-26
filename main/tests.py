import io
import re
import zipfile
from datetime import timedelta
from unittest import mock

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
