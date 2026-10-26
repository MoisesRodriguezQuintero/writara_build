import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0003_assign_tag_owners'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='tag',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tags', to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(name='tag', options={'ordering': ['name']}),
        migrations.AlterUniqueTogether(name='tag', unique_together={('owner', 'name')}),
    ]
