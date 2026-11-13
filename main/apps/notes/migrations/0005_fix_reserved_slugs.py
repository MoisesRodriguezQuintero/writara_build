from django.db import migrations

RESERVED = {'new', 'graph', 'quick', 'autocomplete'}


def fix_reserved_slugs(apps, schema_editor):
    """Notas cuyo slug coincide con una ruta fija (/notes/graph/, /notes/new/…)
    no se podían abrir: se les añade el sufijo -nota."""
    Note = apps.get_model('notes', 'Note')
    for note in Note.objects.filter(slug__in=RESERVED):
        base = f'{note.slug}-nota'
        slug, n = base, 1
        while Note.objects.filter(owner_id=note.owner_id, slug=slug).exists():
            slug = f'{base}-{n}'
            n += 1
        note.slug = slug
        note.save(update_fields=['slug'])


class Migration(migrations.Migration):

    dependencies = [('notes', '0004_tag_owner_required')]

    operations = [migrations.RunPython(fix_reserved_slugs, migrations.RunPython.noop)]
