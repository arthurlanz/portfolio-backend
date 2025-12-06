from django.db import models
from django.core.validators import EmailValidator

class ContactMessage(models.Model):
    name = models.CharField(max_length=200, verbose_name='Nome')
    email = models.EmailField(validators=[EmailValidator()], verbose_name='Email')
    subject = models.CharField(max_length=300, verbose_name='Assunto')
    message = models.TextField(verbose_name='Mensagem')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Data de Envio')
    is_read = models.BooleanField(default=False, verbose_name='Lida')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP')

    class Meta:
        verbose_name = 'Mensagem de Contato'
        verbose_name_plural = 'Mensagens de Contato'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} - {self.subject} ({self.created_at.strftime("%d/%m/%Y %H:%M")})'
