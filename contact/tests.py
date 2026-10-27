from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase

from .models import ContactMessage
from .tasks import deliver

SMTP = dict(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST='smtp.exemplo.com',
    EMAIL_HOST_USER='eu@exemplo.com',
    EMAIL_HOST_PASSWORD='senha-de-app',
    DEFAULT_FROM_EMAIL='eu@exemplo.com',
    CONTACT_EMAIL='destino@exemplo.com',
)

VALID = {
    'name': "Maria D'Ávila",
    'email': 'maria@exemplo.com',
    'subject': 'Vaga de estágio',
    'message': 'Olá! Gostei do seu portfólio e queria conversar.',
}


def make_message():
    return ContactMessage.objects.create(**VALID)


@override_settings(SENDGRID_API_KEY='', **SMTP)
class SmtpDeliveryTests(TestCase):
    def test_envia_por_smtp_com_reply_to(self):
        self.assertTrue(deliver(make_message(), 'Contato: teste', '<p>oi</p>'))
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['destino@exemplo.com'])
        self.assertEqual(sent.reply_to, ['maria@exemplo.com'])
        self.assertEqual(sent.alternatives[0][1], 'text/html')

    def test_sem_provedor_devolve_falso(self):
        with override_settings(EMAIL_HOST_PASSWORD=''):
            self.assertFalse(deliver(make_message(), 'x', '<p>x</p>'))
        self.assertEqual(len(mail.outbox), 0)


@override_settings(SENDGRID_API_KEY='SG.chave', **SMTP)
class FallbackTests(TestCase):
    def test_usa_sendgrid_quando_o_smtp_falha(self):
        with mock.patch('contact.tasks.send_via_smtp', side_effect=OSError('smtp fora')), \
             mock.patch('contact.tasks.send_via_sendgrid', return_value=202) as sendgrid:
            self.assertTrue(deliver(make_message(), 'x', '<p>x</p>'))
        sendgrid.assert_called_once()

    def test_falso_quando_os_dois_falham(self):
        with mock.patch('contact.tasks.send_via_smtp', side_effect=OSError('smtp fora')), \
             mock.patch('contact.tasks.send_via_sendgrid', side_effect=RuntimeError('401')):
            self.assertFalse(deliver(make_message(), 'x', '<p>x</p>'))


class ContactEndpointTests(APITestCase):
    url = '/api/contact/send/'

    @override_settings(SENDGRID_API_KEY='', EMAIL_HOST_PASSWORD='')
    def test_salva_a_mensagem_mesmo_sem_provedor(self):
        response = self.client.post(self.url, VALID, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_aceita_nome_com_apostrofo_e_hifen(self):
        data = {**VALID, 'name': "Ana-Maria D'Ávila Jr."}
        with override_settings(SENDGRID_API_KEY='', EMAIL_HOST_PASSWORD=''):
            self.assertEqual(self.client.post(self.url, data, format='json').status_code, 201)

    def test_recusa_dados_curtos(self):
        data = {**VALID, 'subject': 'oi', 'message': 'curta'}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('subject', response.data['errors'])
        self.assertIn('message', response.data['errors'])
        self.assertEqual(ContactMessage.objects.count(), 0)
