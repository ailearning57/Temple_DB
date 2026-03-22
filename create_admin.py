import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'temple_project.settings')
django.setup()

from users.models import User

if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print("Superuser created successfully (username: admin, password: admin)")
else:
    print("Superuser already exists.")
