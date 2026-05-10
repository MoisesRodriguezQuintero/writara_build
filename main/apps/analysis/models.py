from django.db import models
from main.apps.editor.models import Document

class AnalysisResult(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='analyses')
    word_count = models.IntegerField(default=0)
    sentence_count = models.IntegerField(default=0)
    paragraph_count = models.IntegerField(default=0)
    unique_words = models.IntegerField(default=0)
    lexical_density = models.FloatField(default=0)
    avg_sentence_length = models.FloatField(default=0)
    avg_word_length = models.FloatField(default=0)
    estimated_read_min = models.IntegerField(default=0)
    passive_voice_count = models.IntegerField(default=0)
    long_sentences = models.IntegerField(default=0)
    top_words_json = models.TextField(default='[]')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        get_latest_by = 'created_at'

    def __str__(self):
        return f"Análisis: {self.document.title}"
