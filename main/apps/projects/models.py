from django.conf import settings
from django.db import models

class Project(models.Model):
    STATUS_CHOICES = [
        ('draft','Borrador'),('review','Revisando'),
        ('published','Publicado'),('archived','Archivado'),
    ]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    word_goal = models.IntegerField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    cover_color = models.CharField(max_length=7, default='#6366f1')
    # Proyecto especial de cada usuario donde viven las notas sueltas y las capturas
    # rápidas que no pertenecen a ningún proyecto concreto. No se puede eliminar.
    is_general = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(
                fields=['owner'], condition=models.Q(is_general=True),
                name='one_general_project_per_owner',
            ),
        ]

    def __str__(self):
        return self.name


GENERAL_PROJECT_NAME = 'Notas generales'


def general_project_for(user):
    """Proyecto «Notas generales» del usuario (se crea la primera vez que hace falta)."""
    project, _ = Project.objects.get_or_create(
        owner=user, is_general=True,
        defaults={
            'name': GENERAL_PROJECT_NAME,
            'description': 'Notas sueltas y capturas rápidas que no pertenecen a ningún proyecto.',
            'cover_color': '#8b6f4e',
        },
    )
    return project

class Section(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='draft')
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project.name} — {self.title}"

class Character(models.Model):
    ROLE_CHOICES = [
        ('protagonist','Protagonista'),('antagonist','Antagonista'),
        ('secondary','Secundario'),('other','Otro'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='characters')
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='secondary')
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class Place(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='places')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.project.name})"

class Task(models.Model):
    STATUS_CHOICES = [('todo','Pendiente'),('doing','En progreso'),('done','Hecho')]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='todo')
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class TimelineEvent(models.Model):
    project     = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='events')
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    date_label  = models.CharField(max_length=100, blank=True)  # "Día 1", "Año 3", libre
    order       = models.PositiveIntegerField(default=0)
    characters  = models.ManyToManyField(Character, blank=True, related_name='events')
    places      = models.ManyToManyField(Place, blank=True, related_name='events')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.project.name} — {self.title}"