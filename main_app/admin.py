from django.contrib import admin
from .models import CustomUser
from .forms import CustomUserCreationForm

class CustomUserAdmin(admin.ModelAdmin):
    form = CustomUserCreationForm
    list_display = ('username', 'email', 'role', 'manager')
    list_filter = ('role',)
    search_fields = ('username', 'email')

    def get_form(self, request, obj=None, **kwargs):
        """
        Override the get_form method to pass the current user to the form.
        """
        form = super().get_form(request, obj, **kwargs)

        # Define a wrapper for the form's __init__ to inject the current user
        class CustomFormWrapper(form):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs['user'] = request.user  # Pass the current user
                super().__init__(*args, **inner_kwargs)

        return CustomFormWrapper

    def get_queryset(self, request):
        """
        Restrict Admins to viewing only their subordinates.
        """
        qs = super().get_queryset(request)
        if request.user.role == 'Admin':
            return qs.filter(manager=request.user)
        return qs

    def has_add_permission(self, request):
        """
        Allow add permission for SuperAdmin and Admin only.
        """
        return request.user.role in ['SuperAdmin', 'Admin']

    def has_change_permission(self, request, obj=None):
        """
        Allow change permission for Admin on their subordinates.
        """
        if request.user.role == 'Admin' and obj:
            return obj.manager == request.user
        return request.user.role == 'SuperAdmin'

    def has_delete_permission(self, request, obj=None):
        """
        Allow delete permission for Admin on their subordinates.
        """
        if request.user.role == 'Admin' and obj:
            return obj.manager == request.user
        return request.user.role == 'SuperAdmin'

admin.site.register(CustomUser, CustomUserAdmin)
