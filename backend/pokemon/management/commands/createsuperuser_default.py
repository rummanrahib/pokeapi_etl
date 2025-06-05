from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import IntegrityError

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with default credentials if it doesn\'t exist'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='admin',
            help='Superuser username (default: admin)',
        )
        parser.add_argument(
            '--email',
            default='admin@example.com',
            help='Superuser email (default: admin@example.com)',
        )
        parser.add_argument(
            '--password',
            default='adminpassword',
            help='Superuser password (default: adminpassword)',
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        try:
            if not User.objects.filter(username=username).exists():
                User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(self.style.SUCCESS(f'Successfully created superuser: {username}'))
            else:
                self.stdout.write(self.style.WARNING(f'Superuser {username} already exists'))
        except IntegrityError as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}')) 