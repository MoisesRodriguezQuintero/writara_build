import re
from django.urls import reverse

WIKI_RE = re.compile(r'\[\[([^\]]+)\]\]')

def parse_wiki_links(content, user):
    from .models import Note
    def replace(m):
        title = m.group(1)
        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip().replace(' ', '-')
        note = Note.objects.filter(owner=user, slug=slug).first()
        if note:
            url = reverse('notes:detail', args=[note.slug])
            return f'<a class="wiki-link" href="{url}">{title}</a>'
        url = reverse('notes:create') + f'?title={title}'
        return f'<a class="wiki-link wiki-link--new" href="{url}">{title} +</a>'
    return WIKI_RE.sub(replace, content)

def sync_links(note):
    from .models import Note, NoteLink
    user = note.owner
    found_slugs = set()
    for m in WIKI_RE.finditer(note.content):
        title = m.group(1)
        slug = re.sub(r'[^\w\s-]', '', title.lower()).strip().replace(' ', '-')
        found_slugs.add(slug)
    NoteLink.objects.filter(from_note=note).delete()
    for slug in found_slugs:
        target = Note.objects.filter(owner=user, slug=slug).exclude(pk=note.pk).first()
        if target:
            NoteLink.objects.get_or_create(from_note=note, to_note=target)
