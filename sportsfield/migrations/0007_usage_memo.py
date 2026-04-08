from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sportsfield', '0006_entry_reserved_counts'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='usage_memo',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='sportsfieldentry',
            name='usage_memo',
            field=models.TextField(blank=True),
        ),
    ]
