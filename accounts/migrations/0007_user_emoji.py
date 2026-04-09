from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_alter_user_organization'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='emoji',
            field=models.CharField(blank=True, max_length=10, verbose_name='이모지'),
        ),
    ]
