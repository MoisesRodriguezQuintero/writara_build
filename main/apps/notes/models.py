from django.conf import settings
from django.db import models
from django.utils.text import slugify

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default='#6366f1')

    def __str__(self):
        return self.name

class Note(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    content = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='notes')
    is_favorite = models.BooleanField(default=False)
    is_inbox = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('owner', 'slug')]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title) or 'nota'
            slug = base
            n = 1
            while Note.objects.filter(owner=self.owner, slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def word_count(self):
        import re
        text = re.sub(r'<[^>]+>', ' ', self.content)
        return len(text.split())

class NoteLink(models.Model):
    from_note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='outgoing_links')
    to_note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name='incoming_links')

    class Meta:
        unique_together = [('from_note', 'to_note')]

    def __str__(self):
        return f"{self.from_note} → {self.to_note}"
