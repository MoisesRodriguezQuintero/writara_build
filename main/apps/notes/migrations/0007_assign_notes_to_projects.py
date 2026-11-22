from django.db import migrations

GENERAL_NAME = 'Notas generales'


def assign_notes_to_general_project(apps, schema_editor):
    """Las notas existentes no pertenecían a ningún proyecto: cada usuario con notas
    recibe su proyecto «Notas generales» y todas sus notas pasan a él. Así los
    [[enlaces]] y el grafo siguen igual (todas las notas están en el mismo proyecto)."""
    Note = apps.get_model('notes', 'Note')
    Project = apps.get_model('projects', 'Project')
    owner_ids = (Note.objects.filter(project__isnull=True)
                 .values_list('owner_id', flat=True).distinct())
    for owner_id in list(owner_ids):
        project, _ = Project.objects.get_or_create(
            owner_id=owner_id, is_general=True,
            defaults={
                'name': GENERAL_NAME,
                'description': 'Notas sueltas y capturas rápidas que no pertenecen a ningún proyecto.',
                'cover_color': '#8b6f4e',
            },
        )
        Note.objects.filter(owner_id=owner_id, project__isnull=True).update(project=project)


class Migration(migrations.Migration):

    dependencies = [('notes', '0006_note_project')]

    operations = [migrations.RunPython(assign_notes_to_general_project, migrations.RunPython.noop)]
