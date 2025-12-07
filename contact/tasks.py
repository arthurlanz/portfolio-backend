import threading
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_email_async(message, ip_address):
    """
    Envia email em background usando SendGrid
    """
    def send():
        try:
            email_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                               color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                    .content {{ background: #f9f9f9; padding: 30px; border: 1px solid #e0e0e0; }}
                    .info-box {{ background: white; padding: 20px; margin: 20px 0; border-radius: 5px; 
                                 border-left: 4px solid #667eea; }}
                    .info-label {{ font-weight: bold; color: #667eea; margin-bottom: 5px; }}
                    .message-box {{ background: white; padding: 20px; border-radius: 5px; margin-top: 20px; }}
                    .footer {{ background: #333; color: #999; padding: 20px; text-align: center; 
                              font-size: 12px; border-radius: 0 0 10px 10px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>✉️ Nova Mensagem do Portfolio</h1>
                    </div>
                    <div class="content">
                        <div class="info-box">
                            <div class="info-label">👤 Nome:</div>
                            <div>{message.name}</div>
                        </div>
                        <div class="info-box">
                            <div class="info-label">📧 Email:</div>
                            <div><a href="mailto:{message.email}">{message.email}</a></div>
                        </div>
                        <div class="info-box">
                            <div class="info-label">📝 Assunto:</div>
                            <div>{message.subject}</div>
                        </div>
                        <div class="message-box">
                            <div class="info-label">💬 Mensagem:</div>
                            <p>{message.message}</p>
                        </div>
                        <div style="margin-top: 20px; padding: 15px; background: #e7f3ff; border-radius: 5px;">
                            <small>
                                <strong>📅 Data:</strong> {message.created_at.strftime('%d/%m/%Y às %H:%M')}<br>
                                <strong>🌐 IP:</strong> {ip_address}
                            </small>
                        </div>
                    </div>
                    <div class="footer">
                        <p>Enviado via Portfolio - Arthur Lanznaster</p>
                        <p>Este é um email automático, não responda.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Criar email
            email_message = Mail(
                from_email=settings.DEFAULT_FROM_EMAIL,
                to_emails=settings.CONTACT_EMAIL,
                subject=f'[Portfolio] {message.subject}',
                html_content=email_html
            )

            # Enviar via SendGrid
            sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sg.send(email_message)
            
            logger.info(f'✅ Email enviado com sucesso via SendGrid: {message.name} - Status: {response.status_code}')
        except Exception as e:
            logger.error(f'❌ Erro ao enviar email via SendGrid: {str(e)}')
    
    # Criar e iniciar thread
    thread = threading.Thread(target=send)
    thread.daemon = True
    thread.start()
    logger.info(f'📤 Email agendado via SendGrid para: {message.email}')
