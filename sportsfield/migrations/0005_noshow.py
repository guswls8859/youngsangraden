from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sportsfield', '0004_actual_counts'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='is_noshow',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='sportsfieldentry',
            name='is_noshow',
            field=models.BooleanField(default=False),
        ),
    ]
