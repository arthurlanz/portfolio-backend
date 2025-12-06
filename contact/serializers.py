from rest_framework import serializers
from .models import ContactMessage
import re

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        """Validar nome"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError('Nome deve ter pelo menos 3 caracteres.')
        if not re.match(r'^[a-zA-ZÀ-ÿ\s]+$', value):
            raise serializers.ValidationError('Nome deve conter apenas letras.')
        return value.strip()

    def validate_email(self, value):
        """Validar email"""
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError('Email inválido.')
        return value.lower().strip()

    def validate_subject(self, value):
        """Validar assunto"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError('Assunto deve ter pelo menos 5 caracteres.')
        if len(value) > 300:
            raise serializers.ValidationError('Assunto muito longo (máximo 300 caracteres).')
        return value.strip()

    def validate_message(self, value):
        """Validar mensagem"""
        if len(value.strip()) < 20:
            raise serializers.ValidationError('Mensagem deve ter pelo menos 20 caracteres.')
        if len(value) > 5000:
            raise serializers.ValidationError('Mensagem muito longa (máximo 5000 caracteres).')
        return value.strip()
