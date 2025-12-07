# Portfolio Backend API

API RESTful desenvolvida em Django para gerenciar o sistema de contato do portfolio pessoal. Utiliza Django REST Framework para endpoints de API e SendGrid para envio de emails.

## 🚀 Tecnologias

- Python 3.12
- Django 5.0.1
- Django REST Framework 3.14.0
- PostgreSQL (produção)
- SendGrid (envio de emails)
- Gunicorn (servidor WSGI)
- WhiteNoise (arquivos estáticos)

## 📋 Pré-requisitos

- Python 3.12+
- PostgreSQL (para produção)
- Conta SendGrid (para envio de emails)

## 🔧 Instalação Local

**1. Clone o repositório**

    git clone https://github.com/arthurlanznaster/portfolio-backend.git
    cd portfolio-backend

**2. Crie e ative o ambiente virtual**

Windows:

    python -m venv venv
    venv\Scripts\activate

Linux/Mac:

    python -m venv venv
    source venv/bin/activate

**3. Instale as dependências**

    pip install -r requirements.txt

**4. Configure as variáveis de ambiente**

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

    SECRET_KEY=sua-secret-key-super-secreta-aqui
    DEBUG=True
    ALLOWED_HOSTS=localhost,127.0.0.1
    DATABASE_URL=sqlite:///db.sqlite3
    EMAIL_HOST=smtp.sendgrid.net
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER=apikey
    EMAIL_HOST_PASSWORD=sua-senha-smtp-sendgrid
    DEFAULT_FROM_EMAIL=seu-email@verificado.com
    CONTACT_EMAIL=seu-email@gmail.com
    SENDGRID_API_KEY=SG.sua-api-key-sendgrid-aqui

**5. Execute as migrações**

    python manage.py migrate

**6. Colete arquivos estáticos**

    python manage.py collectstatic --noinput

**7. Inicie o servidor**

    python manage.py runserver

A API estará disponível em http://localhost:8000

## 📡 Endpoints da API

### Health Check

**GET** `/api/contact/health/`

Retorna o status da API.

Resposta:
- `status`: "online"
- `message`: "API do Portfolio funcionando"
- `version`: "1.0.0"

### Enviar Mensagem de Contato

**POST** `/api/contact/send/`

Envia uma nova mensagem de contato.

**Campos obrigatórios:**
- `name` - Nome do remetente
- `email` - Email válido
- `subject` - Assunto da mensagem
- `message` - Conteúdo da mensagem

**Resposta de Sucesso (201):**
- Retorna os dados da mensagem criada

**Resposta de Erro (400):**
- Retorna os erros de validação

### Rate Limiting

- **5 mensagens por hora** por IP
- Retorna `429 Too Many Requests` quando excedido

## 🗂️ Estrutura do Projeto

    portfolio-backend/
    ├── backend/              # Configurações principais do Django
    ├── contact/              # App de contato
    ├── staticfiles/          # Arquivos estáticos coletados
    ├── requirements.txt      # Dependências Python
    ├── build.sh             # Script de build para Render
    ├── .env                 # Variáveis de ambiente
    ├── .gitignore           # Arquivos ignorados
    └── manage.py            # Django management

## 🔒 Variáveis de Ambiente

| Variável | Descrição | Obrigatória |
|----------|-----------|-------------|
| SECRET_KEY | Chave secreta do Django | Sim |
| DEBUG | Modo debug (True/False) | Sim |
| ALLOWED_HOSTS | Hosts permitidos (separados por vírgula) | Sim |
| DATABASE_URL | URL do banco PostgreSQL | Sim (produção) |
| SENDGRID_API_KEY | API Key do SendGrid | Sim |
| EMAIL_HOST | Host SMTP | Sim |
| EMAIL_PORT | Porta SMTP | Sim |
| EMAIL_USE_TLS | Usar TLS (True/False) | Sim |
| EMAIL_HOST_USER | Usuário SMTP | Sim |
| EMAIL_HOST_PASSWORD | Senha SMTP | Sim |
| DEFAULT_FROM_EMAIL | Email remetente padrão | Sim |
| CONTACT_EMAIL | Email para receber mensagens | Sim |

## 🚀 Deploy no Render

1. Crie um novo Web Service no Render
2. Conecte o repositório GitHub
3. Configure:
   - Build Command: `./build.sh`
   - Start Command: `gunicorn backend.wsgi:application`
   - Environment: Python 3
4. Adicione todas as variáveis de ambiente
5. Deploy automático a cada push na branch main

## 🛡️ Segurança

- CORS configurado para permitir requisições do frontend
- Rate limiting por IP (5 req/hora)
- Validação de dados com Django REST Framework
- Proteção CSRF habilitada
- Headers de segurança configurados em produção
- HTTPS obrigatório em produção

## 🧪 Testes

    python manage.py test

## 📝 Licença

Este projeto está sob a licença MIT.

## 👤 Autor

**Arthur Lanznaster**

- GitHub: [@arthurlanznaster](https://github.com/arthurlanz)
- Email: arthurlanznaster@gmail.com

## 🤝 Contribuindo

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

---

Desenvolvido por Arthur Lanznaster
