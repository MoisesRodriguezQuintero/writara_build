import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('notes', '0007_assign_notes_to_projects')]

    operations = [
        migrations.AlterField(
            model_name='note',
            name='project',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='notes', to='projects.project',
            ),
        ),
    ]
