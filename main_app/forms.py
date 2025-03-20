from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from .models import CustomUser,default_sensors_values,heatpump_devices_data

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Username or Email',  # Updated placeholder
            'class': 'form-control',  # Add CSS classes if needed
            'autofocus': True,
        }),
        label="Username",
        required=True, 
        error_messages={
                'required': 'Please Enter Username. (This field cannot be left blank)'
            }
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Password',
            'class': 'form-control',
        }),
        label="Password",
        required=True, 
        error_messages={
                'required': 'Please enter Password. (This field cannot be left blank)'
            }
    )

    class Meta:
        model = get_user_model()  # Use the custom user model
        fields = ['username', 'password']  # Fields for login

class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'manager', 'password']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the current user
        super().__init__(*args, **kwargs)

        # Dynamically filter the role choices
        if user:
            if user.role == 'SuperAdmin':
                self.fields['role'].choices = [
                    ('Admin', 'Admin'),
                    ('Engineer', 'Engineer'),
                    ('User', 'User'),
                ]
            elif user.role == 'Admin':
                self.fields['role'].choices = [
                    ('Engineer', 'Engineer'),
                    ('User', 'User'),
                ]
            else:
                self.fields['role'].choices = []  # No roles available for lower roles


        # Filter manager options based on the user's role
        if user:
            if user.role == 'SuperAdmin':
                self.fields['manager'].queryset = CustomUser.objects.filter(role='SuperAdmin')
            elif user.role == 'Admin':
                self.fields['manager'].queryset = CustomUser.objects.filter(pk=user.pk)  # Admins can only select themselves
            else:
                self.fields['manager'].queryset = CustomUser.objects.none()

    def save(self, commit=True):
        user = super().save(commit=False)

        # Auto-assign manager based on the role
        if user.role == 'Admin':
            user.manager = self.instance.manager  # For SuperAdmin adding Admin
        elif user.role in ['Engineer', 'User']:
            if not user.manager:
                raise forms.ValidationError("You must select an Admin as the manager for Engineers or Users.")
        if commit:
            user.save()
        return user

class CustomHtmlUserCreationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'address', 'role', 'manager', 'password']
        widgets = {
            'password': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the logged-in user
        default_role = kwargs.pop('default_role', None)  # Extract the default role
        super().__init__(*args, **kwargs)

        # Filter roles dynamically to show only the selected role
        if default_role:
            self.fields['role'].choices = [(default_role, default_role)]  # Restrict to default role
            self.fields['role'].initial = default_role
        user_obj = CustomUser.objects.get(username = user.username)
        # Filter managers dynamically
        if user:
            if default_role == 'Admin' and user.role == 'SuperAdmin':
                # Show only the current SuperAdmin in the manager field for Admin role
                self.fields['manager'].queryset = CustomUser.objects.filter(pk=user.pk)
                self.fields['manager'].initial = user
            elif default_role in ['Engineer', 'User'] and user.role == 'SuperAdmin':
                # Show all Admins in the manager field for Engineer or User roles
                self.fields['manager'].queryset = CustomUser.objects.filter(manager = user_obj.id,role='Admin')
            elif default_role in ['Engineer', 'User'] and user.role == 'Admin':
                # Show only the current Admin in the manager field for Engineer or User roles
                self.fields['manager'].queryset = CustomUser.objects.filter(pk=user.pk)
                self.fields['manager'].initial = user

    def save(self, commit=True):
        user = super().save(commit=False)

        # Auto-assign the role and manager based on the context
        if not user.role:
            user.role = self.initial.get('role')  # Default role is pre-assigned
        if not user.manager:
            user.manager = self.initial.get('user')  # Default manager is pre-assigned
        user.set_password(self.cleaned_data['password'])  # Hash the password
        if commit:
            user.save()
        return user
    
class CustomHtmlUserEditForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'phone_number', 'address', 'role', 'manager']


    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Extract the logged-in user
        default_role = kwargs.pop('default_role', None)  # Extract the default role
        super().__init__(*args, **kwargs)

        # Filter roles dynamically to show only the selected role
        if default_role:
            self.fields['role'].choices = [(default_role, default_role)]  # Restrict to default role
            self.fields['role'].initial = default_role

        # Filter managers dynamically
        if user:
            if default_role == 'Admin' and user.role == 'SuperAdmin':
                # Show only the current SuperAdmin in the manager field for Admin role
                self.fields['manager'].queryset = CustomUser.objects.filter(pk=user.pk)
                self.fields['manager'].initial = user
            elif default_role in ['Engineer', 'User'] and user.role == 'SuperAdmin':
                # Show all Admins in the manager field for Engineer or User roles
                self.fields['manager'].queryset = CustomUser.objects.filter(role='Admin')
            elif default_role in ['Engineer', 'User'] and user.role == 'Admin':
                # Show only the current Admin in the manager field for Engineer or User roles
                self.fields['manager'].queryset = CustomUser.objects.filter(pk=user.pk)
                self.fields['manager'].initial = user

    def save(self, commit=True):
        user = super().save(commit=False)

        # Auto-assign the role and manager based on the context
        if not user.role:
            user.role = self.initial.get('role')  # Default role is pre-assigned
        if not user.manager:
            user.manager = self.initial.get('user')  # Default manager is pre-assigned
        if commit:
            user.save()
        return user

class ProfileUpdateForm(forms.ModelForm):
    
    firstName = forms.CharField(max_length=100, required=True)
    lastName = forms.CharField(max_length=100, required=True)
    phoneNumber = forms.CharField(max_length=30, required=True)
    email = forms.EmailField(required=True)
    role = forms.CharField(required=True)
    address = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = CustomUser
        fields = ['firstName', 'lastName', 'phoneNumber', 'email', 'role', 'address']

class default_sensors_valuesEditForm(forms.ModelForm):
    class Meta:
        model = default_sensors_values
        fields = ['current_value']

    def save(self, commit=True):
        user = super().save(commit=False)

        user.save()
        return user
