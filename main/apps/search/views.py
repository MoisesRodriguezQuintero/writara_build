from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from main.apps.editor.models import Document
from main.apps.notes.models import Note
from main.apps.projects.models import Project
from main.apps.accounts.models import UserPreferences

@login_required
def search(request):
    q = request.GET.get('q', '').strip()
    docs, notes, projects = [], [], []
    if q and len(q) >= 2:
        docs = Document.objects.filter(owner=request.user, is_archived=False).filter(
            Q(title__icontains=q) | Q(content__icontains=q))[:8]
        notes = Note.objects.filter(owner=request.user).filter(
            Q(title__icontains=q) | Q(content__icontains=q))[:8]
        projects = Project.objects.filter(owner=request.user).filter(
            Q(name__icontains=q) | Q(description__icontains=q))[:5]
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    return render(request, 'search/results.html', {
        'q': q, 'docs': docs, 'notes': notes, 'projects': projects,
        'prefs': prefs, 'active': 'search',
    })

@login_required
def palette_search(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q and len(q) >= 1:
        docs = Document.objects.filter(owner=request.user, title__icontains=q)[:5]
        notes = Note.objects.filter(owner=request.user, title__icontains=q)[:5]
        for d in docs:
            results.append({'type': 'doc', 'title': d.title, 'url': f'/editor/{d.pk}/', 'icon': '📄'})
        for n in notes:
            results.append({'type': 'note', 'title': n.title, 'url': f'/notes/{n.slug}/', 'icon': '🗒'})
    return JsonResponse({'results': results})
