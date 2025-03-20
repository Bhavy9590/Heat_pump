# yourapp/utils.py
from django.core.mail import send_mail
from django.utils.html import strip_tags

def send_email(subject, message, recipient_list):
    try:
        send_mail(
            subject,
            message,
            'dptesting10@gmail.com',  # Sender's email
            recipient_list,
            fail_silently=False,
        )
    except Exception as e:
        print(e)

def send_html_email(to_email, subject, html_message):
    # Create a plain text version of the HTML content (optional)
    plain_text_message = strip_tags(html_message)

    # Send the HTML email
    send_mail(subject, plain_text_message, 'dptesting10@gmail.com', [to_email], html_message=html_message)