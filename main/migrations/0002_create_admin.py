from django.db import migrations


def create_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    if not User.objects.filter(username='Lab16').exists():
        User.objects.create_superuser('Lab16', 'admin@shop.ru', 'Prac4')


def delete_admin(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    User.objects.filter(username='Lab16').delete()


class Migration(migrations.Migration):
    dependencies = [('main', '0001_initial')]
    operations = [migrations.RunPython(create_admin, delete_admin)]