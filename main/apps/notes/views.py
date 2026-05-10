import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Note, Tag, NoteLink
from .utils import parse_wiki_links, sync_links
from main.apps.accounts.models import UserPreferences

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
    tags = Tag.objects.filter(notes__owner=request.user).distinct()
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
    title = request.GET.get('title', 'Nueva nota')
    note = Note.objects.create(owner=request.user, title=title)
    UserPreferences.objects.get_or_create(user=request.user)
    return redirect('notes:edit', note.slug)

@login_required
def note_edit(request, slug):
    note = get_object_or_404(Note, slug=slug, owner=request.user)
    tags = Tag.objects.all()
    prefs = get_prefs(request.user)
    return render(request, 'notes/edit.html', {
        'note': note, 'tags': tags, 'prefs': prefs, 'active': 'notes'
    })

@login_required
@require_POST
def note_save(request, slug):
    note = get_object_or_404(Note, slug=slug, owner=request.user)
    data = json.loads(request.body)
    note.title = data.get('title', note.title) or 'Sin título'
    note.content = data.get('content', note.content)
    # Handle tags
    tag_names = data.get('tags', [])
    note.tags.clear()
    for name in tag_names:
        tag, _ = Tag.objects.get_or_create(name=name.strip())
        note.tags.add(tag)
    note.save()
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
        'nodes_json': json.dumps(nodes),
        'edges_json': json.dumps(edges),
        'prefs': prefs, 'active': 'notes',
    })

@login_required
@require_POST
def quick_capture(request):
    data = json.loads(request.body)
    content = data.get('content', '').strip()
    if content:
        title = content[:50] + ('...' if len(content) > 50 else '')
        note = Note.objects.create(owner=request.user, title=title, content=content, is_inbox=True)
    return JsonResponse({'ok': True})

@login_required
def note_autocomplete(request):
    q = request.GET.get('q', '')
    notes = Note.objects.filter(owner=request.user, title__icontains=q)[:8]
    return JsonResponse({'results': [{'title': n.title, 'slug': n.slug} for n in notes]})
