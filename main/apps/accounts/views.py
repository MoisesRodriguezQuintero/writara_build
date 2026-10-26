from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegisterForm
from .models import UserPreferences
from main.utils import to_int


def register(request):
    if request.user.is_authenticated:
        return redirect('editor:list')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserPreferences.objects.get_or_create(user=user)
            login(request, user)
            return redirect('editor:list')
    else:
        form = RegisterForm()
    return render(request, 'registration/register.html', {'form': form})


def _choice(value, choices, current):
    """Valor enviado si es una opción válida; si no, se conserva el actual."""
    return value if value in {c for c, _ in choices} else current


@login_required
def profile(request):
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        post = request.POST
        prefs.theme = _choice(post.get('theme'), UserPreferences.THEME_CHOICES, prefs.theme)
        prefs.editor_font = _choice(post.get('editor_font'), UserPreferences.FONT_CHOICES, prefs.editor_font)
        prefs.editor_width = _choice(post.get('editor_width'), UserPreferences.WIDTH_CHOICES, prefs.editor_width)
        prefs.editor_font_size = to_int(post.get('editor_font_size'), prefs.editor_font_size, 10, 40)
        prefs.paragraph_spacing = to_int(post.get('paragraph_spacing'), prefs.paragraph_spacing, 0, 60)
        prefs.text_indent = to_int(post.get('text_indent'), prefs.text_indent, 0, 100)
        prefs.autosave_interval = to_int(post.get('autosave_interval'), prefs.autosave_interval, 5, 600)
        prefs.save()
        messages.success(request, 'Preferencias guardadas.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'prefs': prefs})
