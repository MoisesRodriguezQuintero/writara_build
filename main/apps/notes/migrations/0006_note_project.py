import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0005_fix_reserved_slugs'),
        ('projects', '0003_project_is_general'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='project',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='notes', to='projects.project',
            ),
        ),
    ]
