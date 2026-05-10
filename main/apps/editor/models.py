from django.conf import settings
from django.db import models

class Document(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Borrador'), ('review', 'Revisando'),
        ('published', 'Publicado'), ('archived', 'Archivado'),
    ]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255, default='Sin título')
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    word_goal = models.IntegerField(null=True, blank=True)
    is_favorite = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title

    def word_count(self):
        import re
        text = re.sub(r'<[^>]+>', ' ', self.content)
        return len(text.split())

class DocumentVersion(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='versions')
    content = models.TextField()
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document.title} — {self.created_at:%Y-%m-%d %H:%M}"

class WritingSession(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    words_written = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=0)

    def __str__(self):
        return f"Sesión {self.document.title} — {self.started_at:%Y-%m-%d}"
