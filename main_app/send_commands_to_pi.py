import pika
import json
from datetime import datetime

RABBITMQ_HOST = "localhost"
RABBITMQ_USER = "root"
RABBITMQ_PASSWORD = "Password123*"
EXCHANGE_NAME = "raspberry_exchange"

def send_command_to_raspberry(raspberry_id, command_type, data):
    """
    Sends a command_type to a specific Raspberry Pi using its unique routing key.
    """
    try:
        credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASSWORD)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()

        # Declare a direct exchange
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)

        # Create the message payload
        message_payload = {
            "raspberry_id": raspberry_id,
            "command_type": command_type,
            "data": data,
            "timestamp": str(datetime.now())
        }

        # Publish the message to the specific routing key (raspberry_id)
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=raspberry_id,  # This is the unique routing key
            body=json.dumps(message_payload),
            properties=pika.BasicProperties(delivery_mode=2)  # Persistent message
        )

        print(f"Message sent to Raspberry Pi {raspberry_id}: {message_payload}")
        connection.close()

    except Exception as e:
        print(e)
        print(f"Error sending message to Raspberry Pi {raspberry_id}: {e}")

# send_command_to_raspberry('raspi_1224_1', "this is success")
