from datetime import timezone as dt_timezone
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import ContactMessage
from .emails import build_html, build_subject, build_text, received_at, sender
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
        self.assertTrue(deliver(make_message(), 'Contato: teste', 'oi', '<p>oi</p>'))
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ['destino@exemplo.com'])
        self.assertEqual(len(sent.reply_to), 1)
        self.assertTrue(sent.reply_to[0].endswith('<maria@exemplo.com>'))
        self.assertTrue(sent.from_email.endswith('<eu@exemplo.com>'))
        self.assertEqual(sent.alternatives[0][1], 'text/html')

    def test_sem_provedor_devolve_falso(self):
        with override_settings(EMAIL_HOST_PASSWORD=''):
            self.assertFalse(deliver(make_message(), 'x', 'x', '<p>x</p>'))
        self.assertEqual(len(mail.outbox), 0)


@override_settings(SENDGRID_API_KEY='SG.chave', **SMTP)
class FallbackTests(TestCase):
    def test_usa_sendgrid_quando_o_smtp_falha(self):
        with mock.patch('contact.tasks.send_via_smtp', side_effect=OSError('smtp fora')), \
             mock.patch('contact.tasks.send_via_sendgrid', return_value=202) as sendgrid:
            self.assertTrue(deliver(make_message(), 'x', 'x', '<p>x</p>'))
        sendgrid.assert_called_once()

    def test_falso_quando_os_dois_falham(self):
        with mock.patch('contact.tasks.send_via_smtp', side_effect=OSError('smtp fora')), \
             mock.patch('contact.tasks.send_via_sendgrid', side_effect=RuntimeError('401')):
            self.assertFalse(deliver(make_message(), 'x', 'x', '<p>x</p>'))


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


@override_settings(TIME_ZONE='America/Sao_Paulo', DEFAULT_FROM_EMAIL='Qualquer Nome <eu@exemplo.com>')
class EmailTemplateTests(TestCase):
    def test_escapa_html_digitado_pelo_visitante(self):
        message = ContactMessage.objects.create(
            name='Maria', email='maria@exemplo.com', subject='<b>negrito</b>',
            message='<script>alert(1)</script>\nsegunda linha',
        )
        html = build_html(message, '10.0.0.1')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('segunda linha', html)
        self.assertIn('<br>', html)

    def test_mostra_o_horario_de_brasilia(self):
        message = make_message()
        message.created_at = timezone.datetime(2026, 10, 27, 3, 14, tzinfo=dt_timezone.utc)
        self.assertEqual(received_at(message), '27/10/2026 às 00:14')

    def test_remetente_usa_o_nome_do_portfolio_e_so_o_endereco_configurado(self):
        self.assertIn('eu@exemplo.com', sender())
        self.assertNotIn('Qualquer Nome', sender())

    def test_assunto_e_texto_simples(self):
        message = make_message()
        self.assertIn("Maria D'Ávila", build_subject(message))
        self.assertIn(message.message, build_text(message, None))
        self.assertIn('maria@exemplo.com', build_text(message, None))
