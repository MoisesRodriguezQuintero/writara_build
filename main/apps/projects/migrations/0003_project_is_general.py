from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('projects', '0002_timelineevent')]

    operations = [
        migrations.AddField(
            model_name='project',
            name='is_general',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='project',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_general', True)), fields=('owner',),
                name='one_general_project_per_owner',
            ),
        ),
    ]
