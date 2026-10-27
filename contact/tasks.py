import threading
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, ReplyTo
from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


def smtp_configured():
    return bool(settings.EMAIL_HOST and settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD)


def send_via_smtp(message, subject, html):
    """Envia pelo SMTP configurado em EMAIL_* (por exemplo, Gmail com senha de app)."""
    email = EmailMultiAlternatives(
        subject=subject,
        body=f'{message.name} <{message.email}>\n\n{message.message}',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.CONTACT_EMAIL],
        reply_to=[message.email],
    )
    email.attach_alternative(html, 'text/html')
    email.send(fail_silently=False)


def send_via_sendgrid(message, subject, html):
    """Envia pela API do SendGrid, usado como reserva."""
    email_message = Mail(
        from_email=Email(settings.DEFAULT_FROM_EMAIL, 'Portfolio Arthur Lanznaster'),
        to_emails=settings.CONTACT_EMAIL,
        subject=subject,
        html_content=html,
    )
    email_message.reply_to = ReplyTo(message.email, message.name)
    response = SendGridAPIClient(settings.SENDGRID_API_KEY).send(email_message)
    return response.status_code


def deliver(message, subject, html):
    """Tenta o SMTP e, se falhar, o SendGrid. Devolve True quando algum entregou."""
    if smtp_configured():
        try:
            send_via_smtp(message, subject, html)
            logger.info(f'Email enviado por SMTP: {message.name} ({message.email})')
            return True
        except Exception as error:
            logger.error(f'Falha ao enviar por SMTP: {error}')
    if settings.SENDGRID_API_KEY:
        try:
            status = send_via_sendgrid(message, subject, html)
            logger.info(f'Email enviado pelo SendGrid: {message.name} ({message.email}) - Status: {status}')
            return True
        except Exception as error:
            logger.error(f'Falha ao enviar pelo SendGrid: {error}')
    return False


def send_email_async(message, ip_address):
    """
    Envia email em background usando SendGrid
    """
    def send():
        try:
            email_html = f"""
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        margin: 0;
                        padding: 0;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 20px auto;
                        background: #ffffff;
                        border-radius: 8px;
                        overflow: hidden;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        background: #2c3e50;
                        color: #ffffff;
                        padding: 30px 20px;
                        text-align: center;
                    }}
                    .header h1 {{
                        margin: 0;
                        font-size: 24px;
                        font-weight: 600;
                    }}
                    .content {{
                        padding: 30px;
                    }}
                    .field {{
                        margin-bottom: 20px;
                        padding-bottom: 20px;
                        border-bottom: 1px solid #eee;
                    }}
                    .field:last-child {{
                        border-bottom: none;
                    }}
                    .label {{
                        font-weight: 600;
                        color: #2c3e50;
                        margin-bottom: 5px;
                        font-size: 14px;
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                    }}
                    .value {{
                        color: #555;
                        font-size: 16px;
                    }}
                    .message-content {{
                        background: #f9f9f9;
                        padding: 20px;
                        border-radius: 4px;
                        border-left: 3px solid #2c3e50;
                        margin-top: 10px;
                        white-space: pre-wrap;
                        word-wrap: break-word;
                    }}
                    .metadata {{
                        background: #f0f0f0;
                        padding: 15px;
                        margin-top: 20px;
                        border-radius: 4px;
                        font-size: 13px;
                        color: #666;
                    }}
                    .footer {{
                        background: #f8f9fa;
                        padding: 20px;
                        text-align: center;
                        font-size: 12px;
                        color: #999;
                        border-top: 1px solid #e0e0e0;
                    }}
                    a {{
                        color: #2c3e50;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Nova Mensagem de Contato</h1>
                    </div>
                    
                    <div class="content">
                        <div class="field">
                            <div class="label">Nome</div>
                            <div class="value">{message.name}</div>
                        </div>
                        
                        <div class="field">
                            <div class="label">E-mail</div>
                            <div class="value"><a href="mailto:{message.email}">{message.email}</a></div>
                        </div>
                        
                        <div class="field">
                            <div class="label">Assunto</div>
                            <div class="value">{message.subject}</div>
                        </div>
                        
                        <div class="field">
                            <div class="label">Mensagem</div>
                            <div class="message-content">{message.message}</div>
                        </div>
                        
                        <div class="metadata">
                            <strong>Informações adicionais:</strong><br>
                            Data e hora: {message.created_at.strftime('%d/%m/%Y às %H:%M')}<br>
                            IP de origem: {ip_address}
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Mensagem recebida através do formulário de contato do portfolio<br>
                        Arthur Lanznaster</p>
                    </div>
                </div>
            </body>
            </html>
            """

            subject = f'Contato: {message.subject}'
            if not deliver(message, subject, email_html):
                logger.error(f'Nenhum provedor entregou a mensagem de {message.email} (id {message.id}). '
                             'Ela continua salva no admin.')

        except Exception as e:
            print(f'Erro ao enviar email: {str(e)}')
            logger.error(f'Erro ao enviar email via SendGrid: {str(e)}')
    
    # Executar envio em background
    thread = threading.Thread(target=send)
    thread.daemon = True
    thread.start()
    logger.info(f'Email agendado para envio: {message.email}')
