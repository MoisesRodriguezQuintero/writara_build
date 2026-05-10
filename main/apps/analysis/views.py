from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import AnalysisResult
from .engine import analyze
from main.apps.editor.models import Document
from main.apps.accounts.models import UserPreferences
import json

@login_required
def document_analysis(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    result = AnalysisResult.objects.filter(document=doc).first()
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    top_words = json.loads(result.top_words_json) if result else []
    return render(request, 'analysis/detail.html', {
        'doc': doc, 'result': result, 'top_words': top_words[:20],
        'prefs': prefs, 'active': 'editor',
    })

@login_required
@require_POST
def run_analysis(request, pk):
    doc = get_object_or_404(Document, pk=pk, owner=request.user)
    data = analyze(doc.content)
    result, _ = AnalysisResult.objects.get_or_create(document=doc)
    for k, v in data.items():
        setattr(result, k, v)
    result.save()
    return JsonResponse({'ok': True, **{k: v for k, v in data.items() if k != 'top_words_json'}})
