from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0003_operationsdailydata'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=300, verbose_name='서브 업무명')),
                ('is_done', models.BooleanField(default=False, verbose_name='완료 여부')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='순서')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('daily_task', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='subtasks',
                    to='reports.dailytask',
                    verbose_name='메인 업무',
                )),
            ],
            options={
                'verbose_name': '서브 업무',
                'verbose_name_plural': '서브 업무 목록',
                'ordering': ['order', 'created_at'],
            },
        ),
    ]
