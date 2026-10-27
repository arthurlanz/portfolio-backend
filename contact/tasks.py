import threading
import logging
from email.utils import formataddr
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, ReplyTo
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from .emails import SENDER_NAME, build_html, build_subject, build_text, sender, sender_address

logger = logging.getLogger(__name__)


def smtp_configured():
    return bool(settings.EMAIL_HOST and settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def send_via_smtp(message, subject, text, html):
    """Envia pelo SMTP configurado em EMAIL_* (por exemplo, Gmail com senha de app)."""
    email = EmailMultiAlternatives(
        subject=subject,
        body=text,
        from_email=sender(),
        to=[settings.CONTACT_EMAIL],
        reply_to=[formataddr((message.name, message.email))],
    )
    email.attach_alternative(html, 'text/html')
    email.send(fail_silently=False)


def send_via_sendgrid(message, subject, text, html):
    """Envia pela API do SendGrid, usado como reserva."""
    email_message = Mail(
        from_email=Email(sender_address(), SENDER_NAME),
        to_emails=settings.CONTACT_EMAIL,
        subject=subject,
        html_content=html,
        plain_text_content=text,
    )
    email_message.reply_to = ReplyTo(message.email, message.name)
    response = SendGridAPIClient(settings.SENDGRID_API_KEY).send(email_message)
    return response.status_code


def deliver(message, subject, text, html):
    """Tenta o SMTP e, se falhar, o SendGrid. Devolve True quando algum entregou."""
    if smtp_configured():
        try:
            send_via_smtp(message, subject, text, html)
            logger.info(f'Email enviado por SMTP: {message.name} ({message.email})')
            return True
        except Exception as error:
            logger.error(f'Falha ao enviar por SMTP: {error}')
    if settings.SENDGRID_API_KEY:
        try:
            status = send_via_sendgrid(message, subject, text, html)
            logger.info(f'Email enviado pelo SendGrid: {message.name} ({message.email}) - Status: {status}')
            return True
        except Exception as error:
            logger.error(f'Falha ao enviar pelo SendGrid: {error}')
    return False


def send_email_async(message, ip_address):
    """Envia o e-mail em segundo plano, para a resposta do formulário não esperar o provedor."""
    def send():
        try:
            subject = build_subject(message)
            text = build_text(message, ip_address)
            html = build_html(message, ip_address)
            if not deliver(message, subject, text, html):
                logger.error(f'Nenhum provedor entregou a mensagem de {message.email} (id {message.id}). '
                             'Ela continua salva no admin.')
        except Exception as error:
            logger.error(f'Erro ao montar ou enviar o e-mail: {error}')

    thread = threading.Thread(target=send, daemon=True)
    thread.start()
    logger.info(f'Email agendado para envio: {message.email}')
