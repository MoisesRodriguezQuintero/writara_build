import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Document, DocumentVersion
from main.apps.accounts.models import UserPreferences

def get_prefs(user):
    prefs, _ = UserPreferences.objects.get_or_create(user=user)
    return prefs

@login_required
def document_list(request):
    docs = Document.objects.filter(owner=request.user, is_archived=False)
    recent = docs.order_by('-updated_at')[:20]
    favorites = docs.filter(is_favorite=True)
    prefs = get_prefs(request.user)
    return render(request, 'editor/list.html', {
        'docs': recent, 'favorites': favorites, 'prefs': prefs,
        'active': 'editor'
    })

@login_required
def document_create(request):
    doc = Document.objects.create(owner=request.user, title='Sin título')
    return redirect('editor:edit', doc.pk)

@login_required
def document_edit(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    prefs = get_prefs(request.user)
    versions = doc.versions.all()[:10]
    return render(request, 'editor/editor.html', {
        'doc': doc, 'prefs': prefs, 'versions': versions,
        'word_count': doc.word_count(),
    })

@login_required
@require_POST
def autosave(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    data = json.loads(request.body)
    doc.title = data.get('title', doc.title) or 'Sin título'
    doc.content = data.get('content', doc.content)
    doc.save()
    # Snapshot every 10 saves or 30+ minutes since last version
    versions_count = doc.versions.count()
    should_snapshot = False
    if versions_count == 0:
        should_snapshot = True
    else:
        last = doc.versions.first()
        delta = timezone.now() - last.created_at
        if delta.total_seconds() > 1800:
            should_snapshot = True
    if should_snapshot:
        DocumentVersion.objects.create(
            document=doc, content=doc.content, word_count=doc.word_count()
        )
    return JsonResponse({
        'saved_at': doc.updated_at.strftime('%H:%M:%S'),
        'word_count': doc.word_count(),
    })

@login_required
@require_POST
def document_delete(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    doc.delete()
    return redirect('editor:list')

@login_required
@require_POST
def toggle_favorite(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    doc.is_favorite = not doc.is_favorite
    doc.save()
    return JsonResponse({'is_favorite': doc.is_favorite})

@login_required
def version_restore(request, pk, vid):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    version = get_object_or_404(DocumentVersion, pk=vid, document=doc)
    doc.content = version.content
    doc.save()
    return redirect('editor:edit', pk)

@login_required
def document_export(request, pk, fmt):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    from .exporters import DocumentExporter
    exp = DocumentExporter(doc)
    if fmt == 'markdown':
        content = exp.to_markdown()
        response = HttpResponse(content, content_type='text/markdown')
        response['Content-Disposition'] = f'attachment; filename="{doc.title}.md"'
        return response
    elif fmt == 'html':
        content = exp.to_html()
        response = HttpResponse(content, content_type='text/html')
        response['Content-Disposition'] = f'attachment; filename="{doc.title}.html"'
        return response
    elif fmt == 'txt':
        import re
        content = re.sub(r'<[^>]+>', '', doc.content)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{doc.title}.txt"'
        return response
    elif fmt == 'odt':
        content = exp.to_odt()
    response = HttpResponse(
        content,
        content_type='application/vnd.oasis.opendocument.text'
    )
    response['Content-Disposition'] = f'attachment; filename="{doc.title}.odt"'
    return response
    return redirect('editor:edit', pk)

@login_required
def document_stats(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    from main.apps.analysis.engine import analyze
    stats = analyze(doc.content)
    return JsonResponse(stats)
