"""Monta o e-mail que chega na caixa de entrada quando alguém usa o formulário de contato."""
from email.utils import formataddr, parseaddr
from urllib.parse import quote

from django.conf import settings
from django.utils import timezone
from django.utils.html import escape

SENDER_NAME = 'Portfólio Arthur Lanznaster'
SITE_URL = 'https://arthurlanznaster.vercel.app'

# Cores do portfólio. O e-mail usa estilos inline porque vários clientes ignoram <style>.
INK = '#0f1f33'
SOFT = '#5b6b80'
LINE = '#e3e8ef'
ACCENT = '#2f45d6'
PAPER = '#f3f5f9'


def sender():
    """Remetente com o nome do portfólio, mantendo só o endereço configurado."""
    _, address = parseaddr(settings.DEFAULT_FROM_EMAIL)
    return formataddr((SENDER_NAME, address or settings.DEFAULT_FROM_EMAIL))


def sender_address():
    return parseaddr(settings.DEFAULT_FROM_EMAIL)[1] or settings.DEFAULT_FROM_EMAIL


def received_at(message):
    """Data e hora no fuso do projeto (e não em UTC)."""
    return timezone.localtime(message.created_at).strftime('%d/%m/%Y às %H:%M')


def build_subject(message):
    return f'{message.name} escreveu no portfólio: {message.subject}'


def build_text(message, ip_address):
    return (
        f'Nova mensagem pelo portfólio\n\n'
        f'De: {message.name} <{message.email}>\n'
        f'Assunto: {message.subject}\n\n'
        f'{message.message}\n\n'
        f'---\n'
        f'Recebida em {received_at(message)} (horário de Brasília). IP: {ip_address or "não informado"}.\n'
        f'Para responder, é só usar "Responder": a resposta vai para {message.email}.\n'
    )


def build_html(message, ip_address):
    name = escape(message.name)
    email = escape(message.email)
    subject = escape(message.subject)
    body = escape(message.message).replace('\n', '<br>')
    first_name = escape(message.name.split()[0]) if message.name.split() else name
    reply_link = f'mailto:{quote(message.email)}?subject={quote("Re: " + message.subject)}'
    when = escape(received_at(message))
    ip = escape(ip_address or 'não informado')
    font = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nova mensagem pelo portfólio</title>
</head>
<body style="margin:0;padding:0;background:{PAPER};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{name}: {subject}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER};padding:24px 12px;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border-radius:12px;overflow:hidden;border:1px solid {LINE};font-family:{font};color:{INK};">
      <tr><td style="background:{INK};padding:22px 28px;">
        <div style="font-size:13px;color:#aab6c8;letter-spacing:0.2px;">Portfólio de Arthur Lanznaster</div>
        <div style="font-size:22px;font-weight:700;color:#ffffff;margin-top:4px;">Nova mensagem de contato</div>
      </td></tr>
      <tr><td style="padding:28px 28px 8px 28px;">
        <div style="font-size:13px;color:{SOFT};">De</div>
        <div style="font-size:18px;font-weight:600;margin-top:2px;">{name}</div>
        <div style="margin-top:2px;"><a href="mailto:{email}" style="color:{ACCENT};text-decoration:none;font-size:15px;">{email}</a></div>
      </td></tr>
      <tr><td style="padding:16px 28px 0 28px;">
        <div style="font-size:13px;color:{SOFT};">Assunto</div>
        <div style="font-size:17px;font-weight:600;margin-top:2px;">{subject}</div>
      </td></tr>
      <tr><td style="padding:20px 28px 0 28px;">
        <div style="font-size:13px;color:{SOFT};margin-bottom:8px;">Mensagem</div>
        <div style="border-left:3px solid {ACCENT};background:{PAPER};padding:16px 18px;border-radius:0 8px 8px 0;font-size:16px;line-height:1.6;word-wrap:break-word;">{body}</div>
      </td></tr>
      <tr><td style="padding:24px 28px 28px 28px;">
        <a href="{reply_link}" style="display:inline-block;background:{ACCENT};color:#ffffff;text-decoration:none;font-weight:600;font-size:15px;padding:12px 20px;border-radius:8px;">Responder a {first_name}</a>
      </td></tr>
      <tr><td style="border-top:1px solid {LINE};padding:16px 28px;font-size:12px;color:{SOFT};line-height:1.5;">
        Recebida em {when} (horário de Brasília) &middot; IP {ip}<br>
        Enviada pelo formulário de <a href="{SITE_URL}" style="color:{SOFT};">{SITE_URL.replace('https://', '')}</a>. Ao responder este e-mail, a resposta vai direto para {email}.
      </td></tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""
