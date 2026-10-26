from django.db import migrations


def assign_owners(apps, schema_editor):
    """Las etiquetas eran globales: se reparte una copia por cada usuario que las
    usaba, y las que no usa nadie se eliminan."""
    Tag = apps.get_model('notes', 'Tag')
    Note = apps.get_model('notes', 'Note')
    for tag in Tag.objects.filter(owner__isnull=True):
        owner_ids = list(
            Note.objects.filter(tags=tag).values_list('owner_id', flat=True).distinct()
        )
        if not owner_ids:
            tag.delete()
            continue
        first, rest = owner_ids[0], owner_ids[1:]
        for owner_id in rest:
            clone = Tag.objects.create(owner_id=owner_id, name=tag.name, color=tag.color)
            for note in Note.objects.filter(tags=tag, owner_id=owner_id):
                note.tags.remove(tag)
                note.tags.add(clone)
        tag.owner_id = first
        tag.save(update_fields=['owner'])


class Migration(migrations.Migration):

    dependencies = [('notes', '0002_tag_owner')]

    operations = [migrations.RunPython(assign_owners, migrations.RunPython.noop)]
