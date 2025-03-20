from .models import heatpump_devices_info, default_sensors_values, raspberry_device_id_counter, CustomUser
from datetime import datetime
from django.db import transaction

def generate_next_device_id():
    """
    Generate a new unique device ID based on the current month and year.
    Format: raspi_MMYY_<increment>
    """
    # Get the current month and year as 2 digits
    now = datetime.now()
    month = now.strftime("%m")  # e.g., "12"
    year = now.strftime("%y")   # e.g., "24"
    
    new_prefix = f"raspi_{month}{year}_"

    with transaction.atomic():  # Ensure atomicity for reading and updating the table
        # Get the last device ID entry
        last_entry = raspberry_device_id_counter.objects.all().last()

        if last_entry:
            # Extract the last device ID
            last_device_id = last_entry.current_device_id

            # Check if the prefix matches the current month/year
            if last_device_id.startswith(new_prefix):
                # Increment the last numeric portion
                last_number = int(last_device_id.split('_')[-1])
                new_number = last_number + 1
            else:
                # If the prefix does not match, reset to 1
                new_number = 1
        else:
            # If no previous entries exist, start with 1
            new_number = 1

        # Create the new device ID
        new_device_id = f"{new_prefix}{new_number}"

        if last_entry:
            # Update the table with the new device ID
            last_entry.current_device_id = new_device_id
            last_entry.save()
        else:
            raspberry_device_id_counter.objects.create(current_device_id=new_device_id)

    return new_device_id

# Default devices and sensors
DEFAULT_DEVICES = ["fan", "pump", "compressor", "heater"]
DEFAULT_SENSORS = [
    ("temperature", 30, 30),
    ("voltage", 210, 210),
    ("watt", 1000, 1000),
    ("high_pressure", 1, 1),
    ("low_pressure", 1, 1),
]

def create_default_entries_for_user(user):
    """
    Creates default device and sensor entries for a new user.
    """

    user.raspberry_id = generate_next_device_id()
    user.raspberry_is_active = True
    user.save()

    # Create default devices
    for device_name in DEFAULT_DEVICES:
        heatpump_devices_info.objects.get_or_create(
            fk_user=user,
            device=device_name,
            defaults={"status": False}
        )

    # Create default sensors
    for sensor_name, current_value, default_value in DEFAULT_SENSORS:
        default_sensors_values.objects.get_or_create(
            fk_user=user,
            sensor=sensor_name,
            defaults={
                "current_value": current_value,
                "default_value": default_value
            }
        )
