import os
import json
import time
import mysql.connector
import boto3
from botocore.exceptions import BotoCoreError, ClientError
import threading
from collections import deque
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Logging utilities
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "processamento.log")
_LOG_BUFFER = deque(maxlen=1000)


def _format_log(level, message):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    return f"{ts} [{level}] {message}"


def store_log(message, level="INFO"):
    """Armazena o log em arquivo e no buffer em memória."""
    line = _format_log(level, message)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # não falhar por causa de log
        pass
    _LOG_BUFFER.append(line)


def get_logs(n=100):
    """Retorna as últimas `n` linhas do buffer (mais recentes primeiro)."""
    n = min(n, len(_LOG_BUFFER))
    return list(_LOG_BUFFER)[-n:]


def clear_logs():
    """Limpa o buffer de logs em memória (o arquivo não é apagado)."""
    _LOG_BUFFER.clear()


def log_print(message, level="INFO"):
    print(message)
    store_log(message, level)


def get_setting(env_key: str, prompt: str, default: str = "") -> str:
    value = os.getenv(env_key, "").strip()
    if value:
        return value
    if default:
        answer = input(f"{prompt} [{default}]: ").strip()
        return answer or default
    return input(f"{prompt}: ").strip()


# Configurações (arquivo .env na pasta Processamento/)
log_print("Carregando configuração — use o arquivo .env ou responda aos prompts:")
rds_host = get_setting("DB_HOST", "Host")
rds_user = get_setting("DB_USER", "User")
rds_password = get_setting("DB_PASSWORD", "Password")
rds_database = get_setting("DB_NAME", "Database", "DB_Ingressos")
regiao = get_setting("AWS_REGION", "AWS Region", "us-east-1")
sqs_url_usuarios = get_setting("SQS_URL_USUARIOS", "URL da fila SQS de Usuários")
sqs_url_ingressos = get_setting("SQS_URL_INGRESSOS", "URL da fila SQS de Ingressos")
sqs_url_pedidos = get_setting("SQS_URL_PEDIDOS", "URL da fila SQS de Pedidos")

if os.getenv("DB_HOST"):
    log_print("Configuração carregada do arquivo .env")

# Conexão com o banco de dados
try:
    db = mysql.connector.connect(
        host=rds_host,
        user=rds_user,
        password=rds_password,
        database=rds_database
    )
except mysql.connector.Error as err:
    log_print(f"Erro ao conectar no banco de dados: {err}", level="ERROR")
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
        log_print(f"Erro ao receber mensagem SQS: {err}", level="ERROR")
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
        log_print(str(err), level="ERROR")
        return None, None

    return payload, receipt_handle


def delete_sqs_message(queue_url, receipt_handle):
    if not receipt_handle:
        return
    try:
        sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
    except (BotoCoreError, ClientError) as err:
        log_print(f"Erro ao excluir mensagem SQS: {err}", level="ERROR")

# Operações de banco de dados

def cadastrar_usuario(usuario):
    log_print("Cadastro de Usuário")
    nome = usuario.get("nome")
    email = usuario.get("email")
    senha = usuario.get("senha")
    admin = usuario.get("admin")
    sql = "INSERT INTO Usuarios (Usuario_Nome, Usuario_Email, Usuario_Senha, Usuario_Admin) VALUES (%s, %s, %s, %s);"
    val = (nome, email, senha, admin)
    cursor.execute(sql, val)
    db.commit()
    log_print("Usuário cadastrado com sucesso!")


def editar_usuario(usuario):
    log_print("Edição de Usuário")
    id_usuario = usuario.get("usuario_id")
    nome = usuario.get("nome")
    email = usuario.get("email")
    senha = usuario.get("senha")
    admin = usuario.get("admin")
    sql = "UPDATE Usuarios SET Usuario_Nome = %s, Usuario_Email = %s, Usuario_Senha = %s, Usuario_Admin = %s WHERE Usuario_ID = %s"
    val = (nome, email, senha, admin, id_usuario)
    cursor.execute(sql, val)
    db.commit()
    log_print("Usuário editado com sucesso!")


def excluir_usuario(usuario):
    log_print("Exclusão de Usuário")
    id_usuario = usuario.get("usuario_id")
    sql = "DELETE FROM Usuarios WHERE Usuario_ID = %s"
    val = (id_usuario,)
    cursor.execute(sql, val)
    db.commit()
    log_print("Usuário excluído com sucesso!")


def cadastrar_ingresso(ingresso):
    log_print("Cadastro de Ingresso")
    nome = ingresso.get("nome")
    data = ingresso.get("data")
    valor = ingresso.get("valor")
    quantidade = ingresso.get("quantidade")
    sql = "INSERT INTO Ingressos (Ingresso_Nome, Ingresso_Data, Ingresso_Valor, Ingresso_Quantidade) VALUES (%s, %s, %s, %s)"
    val = (nome, data, valor, quantidade)
    cursor.execute(sql, val)
    db.commit()
    log_print("Ingresso cadastrado com sucesso!")


def editar_ingresso(ingresso):
    log_print("Edição de Ingresso")
    id_ingresso = ingresso.get("ingresso_id")
    nome = ingresso.get("nome")
    data = ingresso.get("data")
    valor = ingresso.get("valor")
    quantidade = ingresso.get("quantidade")
    sql = "UPDATE Ingressos SET Ingresso_Nome = %s, Ingresso_Data = %s, Ingresso_Valor = %s, Ingresso_Quantidade = %s WHERE Ingresso_ID = %s"
    val = (nome, data, valor, quantidade, id_ingresso)
    cursor.execute(sql, val)
    db.commit()
    log_print("Ingresso editado com sucesso!")


def excluir_ingresso(ingresso):
    log_print("Exclusão de Ingresso")
    id_ingresso = ingresso.get("ingresso_id")
    sql = "DELETE FROM Ingressos WHERE Ingresso_ID = %s"
    val = (id_ingresso,)
    cursor.execute(sql, val)
    db.commit()
    log_print("Ingresso excluído com sucesso!")


def cadastrar_pedido(pedido):
    log_print("Cadastro de Pedido")
    id_usuario = pedido.get("usuario_id")
    id_ingresso = pedido.get("ingresso_id")
    tipo_pagamento = pedido.get("tipo_pagamento")
    quantidade = pedido.get("quantidade")
    valor_total = pedido.get("valor_total")
    sql = "INSERT INTO Pedidos (Usuario_ID, Ingresso_ID, Pedido_Tipo_Pag, Pedido_QNT_Ingressos, Pedido_Valor) VALUES (%s, %s, %s, %s, %s)"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade, valor_total)
    cursor.execute(sql, val)
    db.commit()
    log_print("Pedido cadastrado com sucesso!")


def editar_pedido(pedido):
    log_print("Edição de Pedido")
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
    log_print("Pedido editado com sucesso!")


def excluir_pedido(pedido):
    log_print("Exclusão de Pedido")
    id_pedido = pedido.get("pedido_id")
    sql = "DELETE FROM Pedidos WHERE Pedido_ID = %s"
    val = (id_pedido,)
    cursor.execute(sql, val)
    db.commit()
    log_print("Pedido excluído com sucesso!")


def subtrair_estoque(ingresso, pedido):
    if isinstance(ingresso, dict):
        ingresso_id = ingresso.get("ingresso_id") or ingresso.get("Ingresso_ID")
    else:
        ingresso_id = ingresso

    try:
        ingresso_id = int(ingresso_id)
    except Exception:
        log_print(f"ID de ingresso inválido: {ingresso}", level="ERROR")
        return False

    qtd_pedido = None
    if isinstance(pedido, dict):
        qtd_pedido = pedido.get("quantidade") or pedido.get("Pedido_QNT_Ingressos")
    else:
        try:
            qtd_pedido = int(pedido)
        except Exception:
            qtd_pedido = None

    try:
        qtd_pedido = int(qtd_pedido)
    except Exception:
        log_print(f"Quantidade do pedido inválida: {pedido}", level="ERROR")
        return False

    try:
        cursor.execute("SELECT Ingresso_Quantidade FROM Ingressos WHERE Ingresso_ID = %s", (ingresso_id,))
        row = cursor.fetchone()
        if not row:
            log_print(f"Ingresso não encontrado (ID {ingresso_id}).", level="ERROR")
            return False
        quantidade_atual = int(row[0])
    except mysql.connector.Error as e:
        log_print(f"Erro ao buscar quantidade do ingresso: {e}", level="ERROR")
        return False

    nova_quantidade = quantidade_atual - qtd_pedido
    if nova_quantidade < 0:
        log_print(f"Estoque insuficiente para ingresso {ingresso_id}: atual={quantidade_atual}, pedido={qtd_pedido}", level="ERROR")
        return False

    try:
        log_print(f"Subtraindo {qtd_pedido} unidades do ingresso {ingresso_id}")
        sql = "UPDATE Ingressos SET Ingresso_Quantidade = %s WHERE Ingresso_ID = %s"
        val = (nova_quantidade, ingresso_id)
        cursor.execute(sql, val)
        db.commit()
        log_print(f"Quantidade do ingresso {ingresso_id} atualizada para {nova_quantidade}.")
        return True
    except mysql.connector.Error as e:
        db.rollback()
        log_print(f"Erro ao atualizar quantidade do ingresso: {e}", level="ERROR")
        return False

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
        log_print(f"Operação de usuário desconhecida: {operacao}", level="WARNING")


def process_ingresso(payload):
    operacao = payload.get("operacao")
    if operacao == "Cadastro":
        cadastrar_ingresso(payload)
    elif operacao == "Edicao":
        editar_ingresso(payload)
    elif operacao == "Exclusao":
        excluir_ingresso(payload)
    else:
        log_print(f"Operação de ingresso desconhecida: {operacao}", level="WARNING")


def process_pedido(payload):
    operacao = payload.get("operacao")
    if operacao == "Cadastro":
        ingresso_id = payload.get("ingresso_id") or payload.get("Ingresso_ID") or payload.get("ingresso")
        if not subtrair_estoque(ingresso_id, payload):
            log_print("Pedido não processado: erro ao atualizar estoque.", level="ERROR")
            return
        cadastrar_pedido(payload)
    elif operacao == "Edicao":
        editar_pedido(payload)
    elif operacao == "Exclusao":
        excluir_pedido(payload)
    else:
        log_print(f"Operação de pedido desconhecida: {operacao}", level="WARNING")


def process_queue(queue_url, processor):
    payload, receipt_handle = receive_sqs_message(queue_url)
    if not payload:
        return False
    processor(payload)
    delete_sqs_message(queue_url, receipt_handle)
    return True


def process_sqs_queues():
    log_print("Iniciando leitura das filas SQS...")
    while True:
        processed = False
        processed |= process_queue(sqs_url_usuarios, process_usuario)
        processed |= process_queue(sqs_url_ingressos, process_ingresso)
        processed |= process_queue(sqs_url_pedidos, process_pedido)

        if not processed:
            log_print("Nenhuma mensagem na fila no momento. Aguardando 5 segundos...")
            time.sleep(5)


def command_listener():
    """Thread que escuta comandos do usuário enquanto o programa roda.

    Comandos disponíveis:
    - help: mostra comandos
    - show_logs [n]: mostra últimas n linhas (padrão 100)
    - clear_logs: limpa buffer de logs em memória
    - exit: encerra o processo
    """
    while True:
        try:
            cmd = input().strip()
        except EOFError:
            break
        if not cmd:
            continue
        parts = cmd.split()
        action = parts[0].lower()
        if action == "help":
            print("Comandos: help, show_logs [n], clear_logs, exit")
        elif action == "show_logs":
            n = 100
            if len(parts) > 1:
                try:
                    n = int(parts[1])
                except ValueError:
                    print("Número inválido, usando 100")
            logs = get_logs(n)
            for line in logs:
                print(line)
        elif action == "clear_logs":
            clear_logs()
            print("Buffer de logs limpo (arquivo permanece).")
        elif action == "exit":
            log_print("Comando exit recebido. Encerrando.", level="INFO")
            os._exit(0)
        else:
            print(f"Comando desconhecido: {cmd}. Digite 'help' para ajuda.")

if __name__ == "__main__":
    log_print("Executando em modo SQS automático. Pressione Ctrl+C para parar.")
    # inicia listener de comandos em thread
    cmd_thread = threading.Thread(target=command_listener, daemon=True)
    cmd_thread.start()
    log_print("Listener de comandos iniciado. Digite 'help' para ver comandos.")
    try:
        process_sqs_queues()
    except KeyboardInterrupt:
        log_print("Processamento SQS interrompido pelo usuário.", level="INFO")
    finally:
        cursor.close()
        db.close()
