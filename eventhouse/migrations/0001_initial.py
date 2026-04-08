import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EventhouseRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('space_name', models.CharField(max_length=100, verbose_name='공간명')),
                ('title', models.CharField(max_length=200, verbose_name='사용자/내용')),
                ('record_date', models.DateField(verbose_name='날짜')),
                ('time_start', models.TimeField(blank=True, null=True, verbose_name='시작 시간')),
                ('time_end', models.TimeField(blank=True, null=True, verbose_name='종료 시간')),
                ('memo', models.TextField(blank=True, verbose_name='메모')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['record_date', 'time_start'],
            },
        ),
    ]
