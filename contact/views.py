from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import ContactMessage
from .serializers import ContactMessageSerializer
import logging

logger = logging.getLogger(__name__)

class ContactThrottle(AnonRateThrottle):
    rate = '5/hour'  # 5 mensagens por hora por IP

@api_view(['POST'])
@throttle_classes([ContactThrottle])
def send_contact_message(request):
    """
    Endpoint para enviar mensagem de contato
    """
    # Pegar IP do cliente
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')

    # Validar dados
    serializer = ContactMessageSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': 'Dados inválidos.',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Salvar mensagem no banco
        message = serializer.save(ip_address=ip_address)

        # Preparar email
        email_subject = f'[Portfolio] {message.subject}'
        
        # Email em HTML
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

        # Enviar email
        send_mail(
            subject=email_subject,
            message=f"""
            Nova mensagem de contato
            
            Nome: {message.name}
            Email: {message.email}
            Assunto: {message.subject}
            
            Mensagem:
            {message.message}
            
            Data: {message.created_at.strftime('%d/%m/%Y às %H:%M')}
            IP: {ip_address}
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.CONTACT_EMAIL],
            html_message=email_html,
            fail_silently=False,
        )

        logger.info(f'Mensagem de contato enviada: {message.name} - {message.email}')

        return Response({
            'success': True,
            'message': 'Mensagem enviada com sucesso! Responderei em breve.',
            'data': {
                'id': message.id,
                'created_at': message.created_at
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f'Erro ao enviar email: {str(e)}')
        return Response({
            'success': False,
            'message': 'Erro ao enviar mensagem. Tente novamente mais tarde.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def health_check(request):
    """
    Endpoint para verificar se a API está funcionando
    """
    return Response({
        'status': 'online',
        'message': 'Backend do Portfolio funcionando!',
        'version': '1.0.0'
    })
