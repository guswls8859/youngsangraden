from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sportsfield', '0005_noshow'),
    ]

    operations = [
        migrations.AddField(
            model_name='sportsfieldentry',
            name='reserved_adult_count',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='sportsfieldentry',
            name='reserved_child_count',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
    ]
