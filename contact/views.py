from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.conf import settings
from .models import ContactMessage
from .serializers import ContactMessageSerializer
from .tasks import send_email_async  # ← IMPORTAR A FUNÇÃO
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

        # Enviar email em background (não trava!)
        send_email_async(message, ip_address)

        logger.info(f'Mensagem de contato salva: {message.name} - {message.email}')

        return Response({
            'success': True,
            'message': '✅ Mensagem enviada com sucesso! Responderei em breve.',
            'data': {
                'id': message.id,
                'name': message.name,
                'email': message.email,
                'subject': message.subject,
                'created_at': message.created_at
            }
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f'Erro ao processar mensagem: {str(e)}')
        return Response({
            'success': False,
            'message': 'Erro ao processar mensagem. Tente novamente.',
            'error': str(e)
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
