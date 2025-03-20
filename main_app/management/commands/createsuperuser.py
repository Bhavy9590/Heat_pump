from django.contrib.auth.management.commands.createsuperuser import Command as SuperUserCommand
from django.core.management.base import CommandError
from main_app.models import CustomUser  # Use your app's CustomUser model

class Command(SuperUserCommand):
    help = 'Create a superuser and automatically assign the SuperAdmin role.'

    def handle(self, *args, **options):
        # Call the default createsuperuser command to create the user
        super().handle(*args, **options)

        # After creating the superuser, assign the SuperAdmin role
        username = options.get('username')
        if username:
            try:
                user = CustomUser.objects.get(username=username)
                # Check if the user is not already assigned a role
                if user.is_superuser and user.role != 'SuperAdmin':
                    user.role = 'SuperAdmin'  # Assign SuperAdmin role
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created with role 'SuperAdmin'."))
            except CustomUser.DoesNotExist:
                raise CommandError(f"User '{username}' does not exist.")
