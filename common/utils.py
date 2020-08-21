import html2text
from django.core import mail

__send_mail = mail.send_mail


def send_mail(
    subject,
    message,
    from_email,
    recipient_list,
    fail_silently=False,
    auth_user=None,
    auth_password=None,
    connection=None,
    html_message=None,
):

    if not message and html_message:
        message = html2text.html2text(html_message)

    if message and not html_message:
        html_message = f"<html><body><pre>{message}</pre></body></html>"

    return __send_mail(
        subject,
        message,
        from_email,
        recipient_list,
        fail_silently,
        auth_user,
        auth_password,
        connection,
        html_message,
    )
