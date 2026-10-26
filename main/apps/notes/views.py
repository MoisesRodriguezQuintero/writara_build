import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Note, Tag, NoteLink
from .utils import parse_wiki_links, sync_links
from main.apps.accounts.models import UserPreferences
from main.utils import json_body, short_text

def get_prefs(user):
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    return prefs

@login_required
def note_list(request):
    notes = Note.objects.filter(owner=request.user, is_inbox=False)
    tag_filter = request.GET.get('tag')
    search_q = request.GET.get('q', '')
    if tag_filter:
        notes = notes.filter(tags__name=tag_filter)
    if search_q:
        notes = notes.filter(Q(title__icontains=search_q) | Q(content__icontains=search_q))
    tags = Tag.objects.filter(owner=request.user, notes__owner=request.user).distinct()
    inbox = Note.objects.filter(owner=request.user, is_inbox=True)
    prefs = get_prefs(request.user)
    return render(request, 'notes/list.html', {
        'notes': notes, 'tags': tags, 'tag_filter': tag_filter,
        'search_q': search_q, 'inbox': inbox, 'prefs': prefs, 'active': 'notes'
    })

@login_required
def note_detail(request, slug):
    note = get_object_or_404(Note, slug=slug, owner=request.user)
    parsed = parse_wiki_links(note.content, request.user)
    backlinks = NoteLink.objects.filter(to_note=note).select_related('from_note')
    outgoing = NoteLink.objects.filter(from_note=note).select_related('to_note')
    prefs = get_prefs(request.user)
    return render(request, 'notes/detail.html', {
        'note': note, 'content': parsed,
        'backlinks': backlinks, 'outgoing': outgoing, 'prefs': prefs,
        'active': 'notes',
    })

@login_required
def note_create(request):
    title = short_text(request.GET.get('title'), 'Nueva nota')
    note = Note.objects.create(owner=request.user, title=title)
    return redirect('notes:edit', note.slug)

@login_required
def note_edit(request, slug):
    note = get_object_or_404(Note, slug=slug, owner=request.user)
    tags = Tag.objects.filter(owner=request.user)
    prefs = get_prefs(request.user)
    return render(request, 'notes/edit.html', {
        'note': note, 'tags': tags, 'prefs': prefs, 'active': 'notes',
        'note_tags': [t.name for t in note.tags.all()],
    })

@login_required
@require_POST
def note_save(request, slug):
    note = get_object_or_404(Note, slug=slug, owner=request.user)
    data = json_body(request)
    note.title = short_text(data.get('title', note.title), 'Sin título')
    content = data.get('content', note.content)
    note.content = content if isinstance(content, str) else note.content
    # Etiquetas: por usuario, sin vacíos ni duplicados, con límite de longitud
    raw_tags = data.get('tags', [])
    tag_names = []
    for name in raw_tags if isinstance(raw_tags, list) else []:
        name = str(name).strip()[:50]
        if name and name not in tag_names:
            tag_names.append(name)
    note.save()
    note.tags.set([Tag.objects.get_or_create(owner=request.user, name=n)[0] for n in tag_names[:30]])
    sync_links(note)
    return JsonResponse({'saved_at': note.updated_at.strftime('%H:%M:%S'), 'slug': note.slug})

@login_required
@require_POST
def note_delete(request, slug):
    note = get_object_or_404(Note, slug=slug, owner=request.user)
    note.delete()
    return redirect('notes:list')

@login_required
def note_graph(request):
    notes = Note.objects.filter(owner=request.user, is_inbox=False)
    links = NoteLink.objects.filter(from_note__owner=request.user)
    nodes = [{'id': n.pk, 'label': n.title, 'slug': n.slug} for n in notes]
    edges = [{'source': l.from_note_id, 'target': l.to_note_id} for l in links]
    prefs = get_prefs(request.user)
    return render(request, 'notes/graph.html', {
        'nodes': nodes, 'edges': edges,
        'prefs': prefs, 'active': 'notes',
    })

@login_required
@require_POST
def quick_capture(request):
    data = json_body(request)
    content = str(data.get('content', '')).strip()
    if content:
        title = content[:50] + ('...' if len(content) > 50 else '')
        Note.objects.create(owner=request.user, title=title, content=content, is_inbox=True)
    return JsonResponse({'ok': True})

@login_required
def note_autocomplete(request):
    q = request.GET.get('q', '')
    notes = Note.objects.filter(owner=request.user, title__icontains=q)[:8]
    return JsonResponse({'results': [{'title': n.title, 'slug': n.slug} for n in notes]})
