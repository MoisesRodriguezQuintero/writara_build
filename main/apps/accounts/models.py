from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

class UserPreferences(models.Model):
    THEME_CHOICES = [('light', 'Claro'), ('dark', 'Oscuro'), ('system', 'Sistema')]
    FONT_CHOICES = [('serif', 'Serif'), ('sans', 'Sans'), ('mono', 'Mono')]
    WIDTH_CHOICES = [('narrow', 'Estrecho'), ('medium', 'Medio'), ('wide', 'Ancho')]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    editor_font = models.CharField(max_length=10, choices=FONT_CHOICES, default='serif')
    editor_font_size = models.IntegerField(default=17)
    editor_width = models.CharField(max_length=10, choices=WIDTH_CHOICES, default='medium')
    autosave_interval = models.IntegerField(default=30)
    sidebar_collapsed = models.BooleanField(default=False)

    def __str__(self):
        return f"Prefs de {self.user.username}"
