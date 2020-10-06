from django.core import mail

from .mail import send_mail

mail.send_mail = send_mail
