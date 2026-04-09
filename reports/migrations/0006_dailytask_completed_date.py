from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0005_dailytask_end_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailytask',
            name='completed_date',
            field=models.DateField(blank=True, null=True, verbose_name='완료일'),
        ),
    ]
