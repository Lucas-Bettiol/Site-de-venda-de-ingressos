import os
import json
import time
import mysql.connector
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# Configurações
print("Configure as conexões com o banco de dados e AWS SQS:")
rds_host = input("Host: ")
rds_user = input("User: ")
rds_password = input("Password: ")
rds_database = input("Database: ")
regiao = os.getenv("AWS_REGION", "us-east-1")
sqs_url_usuarios = input("URL da fila SQS de Usuários: ")
sqs_url_ingressos = input("URL da fila SQS de Ingressos: ")
sqs_url_pedidos = input("URL da fila SQS de Pedidos: ")

# Conexão com o banco de dados
try:
    db = mysql.connector.connect(
        host=rds_host,
        user=rds_user,
        password=rds_password,
        database=rds_database
    )
except mysql.connector.Error as err:
    print(f"Erro ao conectar no banco de dados: {err}")
    raise

cursor = db.cursor()
sqs = boto3.client("sqs", region_name=regiao)

# Helper SQS

def parse_sqs_body(body):
    if isinstance(body, str):
        return json.loads(body)
    if isinstance(body, dict):
        return body
    raise ValueError("Corpo da mensagem SQS inválido")


def receive_sqs_message(queue_url):
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=10,
            VisibilityTimeout=30
        )
    except (BotoCoreError, ClientError) as err:
        print(f"Erro ao receber mensagem SQS: {err}")
        return None, None

    messages = response.get("Messages")
    if not messages:
        return None, None

    message = messages[0]
    receipt_handle = message.get("ReceiptHandle")
    body = message.get("Body")

    try:
        payload = parse_sqs_body(body)
    except ValueError as err:
        print(err)
        return None, None

    return payload, receipt_handle


def delete_sqs_message(queue_url, receipt_handle):
    if not receipt_handle:
        return
    try:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    except (BotoCoreError, ClientError) as err:
        print(f"Erro ao excluir mensagem SQS: {err}")

# Operações de banco de dados

def cadastrar_usuario(usuario):
    print("Cadastro de Usuário")
    nome = usuario.get("nome")
    email = usuario.get("email")
    senha = usuario.get("senha")
    admin = usuario.get("admin")
    sql = "INSERT INTO Usuarios (Usuario_Nome, Usuario_Email, Usuario_Senha, Usuario_Admin) VALUES (%s, %s, %s, %s);"
    val = (nome, email, senha, admin)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário cadastrado com sucesso!")


def editar_usuario(usuario):
    print("Edição de Usuário")
    id_usuario = usuario.get("usuario_id")
    nome = usuario.get("nome")
    email = usuario.get("email")
    senha = usuario.get("senha")
    admin = usuario.get("admin")
    sql = "UPDATE Usuarios SET Usuario_Nome = %s, Usuario_Email = %s, Usuario_Senha = %s, Usuario_Admin = %s WHERE Usuario_ID = %s"
    val = (nome, email, senha, admin, id_usuario)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário editado com sucesso!")


def excluir_usuario(usuario):
    print("Exclusão de Usuário")
    id_usuario = usuario.get("usuario_id")
    sql = "DELETE FROM Usuarios WHERE Usuario_ID = %s"
    val = (id_usuario,)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário excluído com sucesso!")


def cadastrar_ingresso(ingresso):
    print("Cadastro de Ingresso")
    nome = ingresso.get("nome")
    data = ingresso.get("data")
    valor = ingresso.get("valor")
    quantidade = ingresso.get("quantidade")
    sql = "INSERT INTO Ingressos (Ingresso_Nome, Ingresso_Data, Ingresso_Valor, Ingresso_Quantidade) VALUES (%s, %s, %s, %s)"
    val = (nome, data, valor, quantidade)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso cadastrado com sucesso!")


def editar_ingresso(ingresso):
    print("Edição de Ingresso")
    id_ingresso = ingresso.get("ingresso_id")
    nome = ingresso.get("nome")
    data = ingresso.get("data")
    valor = ingresso.get("valor")
    quantidade = ingresso.get("quantidade")
    sql = "UPDATE Ingressos SET Ingresso_Nome = %s, Ingresso_Data = %s, Ingresso_Valor = %s, Ingresso_Quantidade = %s WHERE Ingresso_ID = %s"
    val = (nome, data, valor, quantidade, id_ingresso)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso editado com sucesso!")


def excluir_ingresso(ingresso):
    print("Exclusão de Ingresso")
    id_ingresso = ingresso.get("ingresso_id")
    sql = "DELETE FROM Ingressos WHERE Ingresso_ID = %s"
    val = (id_ingresso,)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso excluído com sucesso!")


def cadastrar_pedido(pedido):
    print("Cadastro de Pedido")
    id_usuario = pedido.get("usuario_id")
    id_ingresso = pedido.get("ingresso_id")
    tipo_pagamento = pedido.get("tipo_pagamento")
    quantidade = pedido.get("quantidade")
    valor_total = pedido.get("valor_total")
    sql = "INSERT INTO Pedidos (Usuario_ID, Ingresso_ID, Pedido_Tipo_Pag, Pedido_QNT_Ingressos, Pedido_Valor) VALUES (%s, %s, %s, %s, %s)"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade, valor_total)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido cadastrado com sucesso!")


def editar_pedido(pedido):
    print("Edição de Pedido")
    id_pedido = pedido.get("pedido_id")
    id_usuario = pedido.get("usuario_id")
    id_ingresso = pedido.get("ingresso_id")
    tipo_pagamento = pedido.get("tipo_pagamento")
    quantidade = pedido.get("quantidade")
    valor_total = pedido.get("valor_total")
    sql = "UPDATE Pedidos SET Usuario_ID = %s, Ingresso_ID = %s, Pedido_Tipo_Pag = %s, Pedido_QNT_Ingressos = %s, Pedido_Valor = %s WHERE Pedido_ID = %s"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade, valor_total, id_pedido)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido editado com sucesso!")


def excluir_pedido(pedido):
    print("Exclusão de Pedido")
    id_pedido = pedido.get("pedido_id")
    sql = "DELETE FROM Pedidos WHERE Pedido_ID = %s"
    val = (id_pedido,)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido excluído com sucesso!")

# Processamento de mensagens

def process_usuario(payload):
    operacao = payload.get("operacao")
    if operacao == "Cadastro":
        cadastrar_usuario(payload)
    elif operacao == "Edicao":
        editar_usuario(payload)
    elif operacao == "Exclusao":
        excluir_usuario(payload)
    else:
        print(f"Operação de usuário desconhecida: {operacao}")


def process_ingresso(payload):
    operacao = payload.get("operacao")
    if operacao == "Cadastro":
        cadastrar_ingresso(payload)
    elif operacao == "Edicao":
        editar_ingresso(payload)
    elif operacao == "Exclusao":
        excluir_ingresso(payload)
    else:
        print(f"Operação de ingresso desconhecida: {operacao}")


def process_pedido(payload):
    operacao = payload.get("operacao")
    if operacao == "Cadastro":
        cadastrar_pedido(payload)
    elif operacao == "Edicao":
        editar_pedido(payload)
    elif operacao == "Exclusao":
        excluir_pedido(payload)
    else:
        print(f"Operação de pedido desconhecida: {operacao}")


def process_queue(queue_url, processor):
    payload, receipt_handle = receive_sqs_message(queue_url)
    if not payload:
        return False
    processor(payload)
    delete_sqs_message(queue_url, receipt_handle)
    return True


def process_sqs_queues():
    print("Iniciando leitura das filas SQS...")
    while True:
        processed = False
        processed |= process_queue(sqs_url_usuarios, process_usuario)
        processed |= process_queue(sqs_url_ingressos, process_ingresso)
        processed |= process_queue(sqs_url_pedidos, process_pedido)

        if not processed:
            print("Nenhuma mensagem na fila no momento. Aguardando 5 segundos...")
            time.sleep(5)

if __name__ == "__main__":
    print("Executando em modo SQS automático. Pressione Ctrl+C para parar.")
    try:
        process_sqs_queues()
    except KeyboardInterrupt:
        print("Processamento SQS interrompido pelo usuário.")
    finally:
        cursor.close()
        db.close()
