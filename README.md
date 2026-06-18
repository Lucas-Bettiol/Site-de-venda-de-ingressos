# TicketFlow - Sistema de Venda de Ingressos

Sistema web de venda e gerenciamento de ingressos para eventos, com arquitetura orientada a mensagens via AWS SQS. O projeto é composto por três módulos independentes: o site com painel do cliente e do administrador, um serviço de processamento assíncrono e um módulo de checkout interativo.

---

## Estrutura do Projeto

```
Site-de-venda-de-ingressos/
├── site de ticket/          # Frontend (HTML/CSS/JS) + API Flask
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   ├── api.py
│   ├── requirements.txt
│   └── .env.example
├── Processamento/           # Serviço de processamento SQS
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
├── ingressos-checkout/      # Módulo de checkout interativo via terminal
│   ├── checkout_ingressos.py
│   ├── requirements.txt
│   └── .env.example
└── DB/
    └── DB_Ingressos.sql     # Script de criação do banco
```

---

## Pré-requisitos

- Python 3.10 ou superior
- MySQL 8.0 ou superior
- Conta AWS com permissão para SQS (opcional para testes locais)

---

## Banco de Dados

Importe o script SQL para criar o schema e as tabelas:

```sql
mysql -u root -p < DB/DB_Ingressos.sql
```

O script cria o banco `DB_Ingressos` com três tabelas:

- `Usuarios` - dados de autenticação e perfil (cliente ou administrador)
- `Ingressos` - eventos disponíveis para venda
- `Pedidos` - registro de compras realizadas

---

## Modulo 1 - Site e API

O frontend em HTML/CSS/JS consome uma API REST em Flask. O painel do cliente permite visualizar eventos, comprar ingressos e acompanhar pedidos. O painel do administrador oferece dashboard com estatísticas, gerenciamento de eventos, pedidos e usuários.

### Configuracao

```bash
cd "site de ticket"
cp .env.example .env
```

Preencha o `.env`:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=DB_Ingressos

AWS_REGION=us-east-1
SQS_URL_USUARIOS=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_INGRESSOS=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_PEDIDOS=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_CONFIRMACAO=https://sqs.us-east-1.amazonaws.com/...

PORT=5000
```

### Instalacao e execucao

```bash
pip install -r requirements.txt
python api.py
```

Acesse `http://localhost:5000`.

### Endpoints da API

| Metodo | Rota | Descricao |
|--------|------|-----------|
| GET | `/api/health` | Verifica conexao com banco e SQS |
| POST | `/api/login` | Autenticacao de usuario |
| GET | `/api/ingressos` | Lista todos os eventos |
| GET | `/api/ingressos/<id>` | Detalhe de um evento |
| GET | `/api/usuarios` | Lista todos os usuarios (admin) |
| GET | `/api/pedidos` | Lista todos os pedidos (admin) |
| GET | `/api/pedidos/usuario/<id>` | Pedidos de um usuario |
| GET | `/api/stats` | Estatisticas gerais |
| POST | `/api/sqs/usuarios` | Envia operacao de usuario para SQS |
| POST | `/api/sqs/ingressos` | Envia operacao de ingresso para SQS |
| POST | `/api/sqs/pedidos` | Envia pedido de compra para SQS |
| POST | `/api/confirmacoes` | Recebe confirmacao de pedido processado |

---

## Modulo 2 - Processamento

Servico que escuta continuamente tres filas SQS (usuarios, ingressos, pedidos) e aplica as operacoes no banco de dados. Suporta cadastro, edicao e exclusao para cada entidade. No caso de pedidos, tambem subtrai o estoque do ingresso correspondente.

### Configuracao

```bash
cd Processamento
cp .env.example .env
```

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=DB_Ingressos

AWS_REGION=us-east-1
SQS_URL_USUARIOS=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_INGRESSOS=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_PEDIDOS=https://sqs.us-east-1.amazonaws.com/...
```

### Execucao

```bash
pip install -r requirements.txt
python app.py
```

O servico roda em loop ate ser interrompido com `Ctrl+C`. Logs sao gravados em `Processamento/logs/processamento.log`. Comandos disponiveis durante a execucao:

| Comando | Descricao |
|---------|-----------|
| `help` | Lista os comandos |
| `show_logs [n]` | Exibe as ultimas n linhas de log (padrao: 100) |
| `clear_logs` | Limpa o buffer de log em memoria |
| `exit` | Encerra o processo |

---

## Modulo 3 - Checkout Interativo

Script de terminal para realizar o checkout de ingressos diretamente, sem passar pelo frontend. Util para testes e operacoes manuais. Suporta tambem um listener SQS proprio para processar pedidos recebidos na fila.

### Configuracao

```bash
cd ingressos-checkout
cp .env.example .env
```

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sua_senha
DB_NAME=DB_Ingressos

AWS_REGION=us-east-1
SQS_URL_PEDIDOS=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_SAIDA=https://sqs.us-east-1.amazonaws.com/...
SQS_URL_SAIDA_WEB=https://sqs.us-east-1.amazonaws.com/...
```

### Execucao

```bash
pip install -r requirements.txt
python checkout_ingressos.py
```

Opcoes disponiveis no menu:

- `1` - Realizar checkout interativo (solicita ID do usuario, ID do ingresso, quantidade e forma de pagamento)
- `2` - Visualizar historico de pedidos de um usuario
- `3` - Iniciar listener SQS para processar pedidos da fila automaticamente

### Formas de pagamento suportadas

- Cartao de credito (parcelamento em ate 12x)
- Boleto bancario (vencimento em 2 dias)
- PIX

---

## Fluxo da Aplicacao

```
Frontend (index.html)
       |
       v
   API Flask (api.py)
       |
       +-- Leitura direta do banco (listagens, login, stats)
       |
       +-- Escrita via SQS (cadastro/edicao/exclusao/pedidos)
              |
              v
       Processamento (app.py)
              |
              v
        MySQL (DB_Ingressos)
```

Pedidos de compra passam pela fila `SQS_URL_PEDIDOS`. O modulo de Processamento subtrai o estoque e registra o pedido. A confirmacao pode ser enviada de volta para o frontend via `SQS_URL_SAIDA_WEB` e recebida no endpoint `/api/confirmacoes`.

---

## Dependencias

Todos os modulos utilizam:

```
mysql-connector-python>=8.0.0
boto3>=1.28.0
python-dotenv>=1.0.0
```

O modulo `site de ticket` adiciona:

```
flask>=3.0.0
flask-cors>=4.0.0
```


