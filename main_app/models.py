from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('SuperAdmin', 'SuperAdmin'),
        ('Admin', 'Admin'),
        ('Engineer', 'Engineer'),
        ('User', 'User'),
    ]
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='SuperAdmin')
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    raspberry_id = models.CharField(max_length=50, blank=True, null=True)
    raspberry_is_active = models.BooleanField(blank=True,null=True)
    remember_token = models.CharField(max_length=200, blank=True, null=True)
    otp_number = models.IntegerField(blank=True, null=True)
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subordinates'
    )

    def save(self, *args, **kwargs):
        if self.is_superuser and not self.role:  # Ensure superusers are SuperAdmins
            self.role = 'SuperAdmin'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
class raspberry_device_id_counter(models.Model):
    current_device_id = models.CharField(max_length=100, verbose_name="Device ID")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class raspberry_devices_start_stop_info(models.Model):
    TYPE_CHOICES = [
        ('Start', 'Start'),
        ('Stop', 'Stop'),
        ('Reboot', 'Reboot'),
    ]
    fk_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="User")
    restart_by = models.CharField(max_length=20, default='Restart By')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='Reboot')
    created_at = models.DateTimeField(auto_now_add=True)

class heatpump_devices_info(models.Model):
    fk_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Heatpump Info")
    device = models.CharField(max_length=100, verbose_name="Device Name")
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class heatpump_devices_errors(models.Model):
    fk_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Heatpump Info")
    error_type = models.CharField(max_length=100, verbose_name="Error Type")
    error = models.CharField(max_length=500, verbose_name="Error")
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class heatpump_devices_data(models.Model):
    fk_heatpump_device = models.ForeignKey(heatpump_devices_info, on_delete=models.CASCADE, verbose_name="Heatpump Info")
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class default_sensors_values(models.Model):
    fk_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name="Heatpump Sensor Info")
    sensor = models.CharField(max_length=100, verbose_name="Sensor Name")
    current_value = models.IntegerField(default=0)
    default_value = models.IntegerField(default=0)
    max_current_value = models.IntegerField(default=0)
    max_default_value = models.IntegerField(default=0)
    bypass_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class sensors_data(models.Model):
    fk_heatpump_sensor = models.ForeignKey(default_sensors_values, on_delete=models.CASCADE, verbose_name="Heatpump Sensors")
    data = models.IntegerField(blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)
