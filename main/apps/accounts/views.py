from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from .models import User, UserPreferences

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserPreferences.objects.create(user=user)
            login(request, user)
            return redirect('editor:list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def profile(request):
    prefs, _ = UserPreferences.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        prefs.theme = request.POST.get('theme', 'dark')
        prefs.editor_font = request.POST.get('editor_font', 'serif')
        prefs.editor_font_size = int(request.POST.get('editor_font_size', 17))
        prefs.editor_width = request.POST.get('editor_width', 'medium')
        prefs.autosave_interval = int(request.POST.get('autosave_interval', 30))
        prefs.save()
        messages.success(request, 'Preferencias guardadas.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'prefs': prefs})
