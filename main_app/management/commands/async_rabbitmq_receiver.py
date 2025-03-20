import asyncio
import json
import pika
import aio_pika
from asgiref.sync import sync_to_async
from django.db import connection
from django.db.utils import OperationalError
from django.core.management.base import BaseCommand
from main_app.models import CustomUser, default_sensors_values, sensors_data, heatpump_devices_info, heatpump_devices_data, heatpump_devices_errors


async def save_to_db_sensor_data(raspberry_id, command_type, data):
    for attempt in range(3):  # Retry up to 3 times
        try:
            # Ensure the database connection is alive
            if connection.connection and not connection.is_usable():
                await sync_to_async(connection.close)()
                await sync_to_async(connection.ensure_connection)()

            user = await CustomUser.objects.aget(raspberry_id=raspberry_id)
            if command_type == 'sensor_data':
                for sensor_name, sensor_value in data.items():
                    sensor_obj = await default_sensors_values.objects.aget(fk_user=user, sensor=sensor_name)
                    await sensors_data.objects.acreate(fk_heatpump_sensor=sensor_obj, data=sensor_value)
            elif command_type == 'update_heatpump_devices_info':
                for sensor_name, sensor_value in data.items():
                    sensor_obj = await heatpump_devices_info.objects.aget(fk_user=user, device=sensor_name)
                    sensor_obj.status = sensor_value
                    await sync_to_async(sensor_obj.save)()
                    await heatpump_devices_data.objects.acreate(fk_heatpump_device=sensor_obj, status=sensor_value)
            elif command_type == 'insert_heatpump_devices_error':
                for sensor_name, sensor_value in data.items():
                    await heatpump_devices_errors.objects.acreate(fk_user=user,error_type=sensor_name, error=sensor_value)
            elif command_type == 'update_raspberry_is_active':
                for sensor_name, sensor_value in data.items():
                    user.raspberry_is_active = sensor_value
                    await sync_to_async(user.save)()

            break  # Break out of the retry loop on success
        except OperationalError as e:
            print(f"Database connection error: {e}. Retrying...")
            try:
                await sync_to_async(connection.close)()
                await sync_to_async(connection.ensure_connection)()
            except Exception as e:
                print(f"Connection closing error {e}.")
            if attempt == 2:  # Final attempt
                raise e

async def async_rabbitmq_receiver():
    """
    Asynchronous RabbitMQ message receiver.
    """
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost/")
    channel = await connection.channel()

    # Declare the queue
    queue = await channel.declare_queue("sensor_data", durable=True)

    print("Waiting for messages. To exit, press CTRL+C")

    async def on_message(message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                raspberry_id = body.get("raspberry_id")
                command_type = body.get("command_type")
                data = body.get("data")

                if command_type == "sensor_data" or command_type == "update_heatpump_devices_info" or command_type == "insert_heatpump_devices_error" or command_type == "update_raspberry_is_active":
                    await save_to_db_sensor_data(raspberry_id, command_type, data)
                    print(f"Processed: {raspberry_id} -> {data}")

            except Exception as e:
                print(f"Error processing message: {e}")

    # Start consuming
    await queue.consume(on_message)

    try:
        await asyncio.Future()  # Keep the event loop running forever
    finally:
        await connection.close()


class Command(BaseCommand):
    help = "Start an asynchronous RabbitMQ receiver"

    def handle(self, *args, **options):
        """
        Entry point for the Django management command.
        """
        asyncio.run(async_rabbitmq_receiver())
