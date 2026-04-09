from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0004_subtask'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailytask',
            name='end_date',
            field=models.DateField(blank=True, null=True, verbose_name='목표 완료일'),
        ),
    ]
