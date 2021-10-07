from django.core import mail

from .mail import mail_admins, send_mail

mail.send_mail = send_mail
mail.mail_admins = mail_admins
