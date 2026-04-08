from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sportsfield', '0003_reservation_adult_count_reservation_applied_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='actual_adult_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='reservation',
            name='actual_child_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sportsfieldentry',
            name='actual_adult_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='sportsfieldentry',
            name='actual_child_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
