import mysql.connector
from datetime import datetime, timedelta
import random
import string
import json
import time
import boto3
from botocore.exceptions import BotoCoreError, ClientError

# ── CONEXÃO ────────────────────────────────────

print("Configure a conexão com o banco de dados MySQL")
host     = input("Host: ")
user     = input("User: ")
password = input("Password: ")
database = input("Database (padrão DB_Ingressos): ") or "DB_Ingressos"
region   = input("AWS Region (padrão us-east-1): ").strip() or "us-east-1"
sqs_url_entrada = input("URL da fila SQS de Pedidos (deixe vazio para não usar listener): ").strip()
sqs_url_saida = input("URL da fila SQS de confirmação (deixe vazio para não enviar): ").strip()

db = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)

cursor = db.cursor()

# ── HELPERS ────────────────────────────────────

def formatar_brl(valor: float) -> str:
    """Recebe valor em reais (float) e retorna string formatada."""
    try:
        reais = float(valor)
    except Exception:
        reais = 0.0
    return f"R$ {reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ── LEITURA DO BANCO (somente SELECT) ──────────

def buscar_usuario(cursor, usuario_id: int) -> dict | None:
    cursor.execute(
        """SELECT Usuario_ID, Usuario_Nome, Usuario_Email
           FROM Usuarios
           WHERE Usuario_ID = %s""",
        (usuario_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "Usuario_ID":    row[0],
        "Nome":          row[1],
        "Email":         row[2],
    }

def buscar_ingresso(cursor, ingresso_id: int) -> dict | None:
    cursor.execute(
        """SELECT Ingresso_ID, Ingresso_Nome, Ingresso_Data,
                  Ingresso_Valor, Ingresso_Quantidade
           FROM Ingressos
           WHERE Ingresso_ID = %s""",
        (ingresso_id,)
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "Ingresso_ID":        row[0],
        "Ingresso_Nome":      row[1],
        "Ingresso_Data":      row[2],
        "Ingresso_Valor":     row[3],
        "Ingresso_Quantidade": row[4],
    }

def listar_pedidos_usuario(cursor, usuario_id: int):
    """Exibe histórico de pedidos do usuário (somente leitura)."""
    cursor.execute(
        """SELECT p.Pedido_ID, i.Ingresso_Nome, p.Pedido_QNT_Ingressos,
                  p.Pedido_Tipo_Pag, p.Pedido_Valor
           FROM Pedidos p
           JOIN Ingressos i ON p.Ingresso_ID = i.Ingresso_ID
           WHERE p.Usuario_ID = %s
           ORDER BY p.Pedido_ID DESC""",
        (usuario_id,)
    )
    rows = cursor.fetchall()
    if not rows:
        print("Nenhum pedido encontrado para este usuário.")
        return

    print(f"\n{'ID':<6} {'Evento':<32} {'Qtd':<5} {'Pagamento':<10} {'Total'}")
    print("─" * 68)
    for row in rows:
        pid, nome, qtd, tipo, valor = row
        print(f"{pid:<6} {nome[:30]:<32} {qtd:<5} {tipo:<10} {formatar_brl(valor)}")

# ── PROCESSAMENTO DE PAGAMENTO ─────────────────

def processar_pagamento_credito(total_reais: float) -> dict:
    print("\n── Pagamento por Cartão de Crédito ──")
    numero   = input("Número do cartão (16 dígitos): ").replace(" ", "")
    nome     = input("Nome no cartão: ")
    validade = input("Validade (MM/AA): ")
    cvv      = input("CVV: ")
    parcelas = int(input("Parcelas (1-12): ") or "1")

    if len(numero) != 16 or not numero.isdigit():
        return {"sucesso": False, "mensagem": "Número do cartão inválido."}
    if len(cvv) not in (3, 4) or not cvv.isdigit():
        return {"sucesso": False, "mensagem": "CVV inválido."}
    if not nome.strip():
        return {"sucesso": False, "mensagem": "Nome do titular não informado."}

    parcela = float(total_reais) / parcelas
    print(f"\n  {parcelas}x de {formatar_brl(parcela)} — Total: {formatar_brl(total_reais)}")

    # Ponto de integração com gateway (Stripe, Cielo, PagSeguro, etc.)
    # response = gateway.charge(numero, cvv, validade, int(round(total_reais * 100)))

    return {
        "sucesso":        True,
        "tipo_pagamento": "credito",
        "parcelas":       parcelas,
        "total_pago":     total_reais,
        "mensagem":       "Pagamento no crédito aprovado!",
    }

def processar_pagamento_boleto(total_reais: float) -> dict:
    print("\n── Pagamento por Boleto Bancário ──")
    vencimento = (datetime.now() + timedelta(days=2)).strftime("%d/%m/%Y")

    def _seg():
        return ''.join(random.choices(string.digits, k=5))

    # Para o código numérico usamos centavos sem alterar lógica do layout
    valor_centavos = str(int(round(float(total_reais) * 100)))
    codigo = (
        f"34191.{_seg()} {_seg()}.{_seg()}0 "
        f"{_seg()}.{_seg()}0 1 {valor_centavos.zfill(14)}"
    )

    print(f"\n  Vencimento : {vencimento}")
    print(f"  Valor      : {formatar_brl(total_reais)}")
    print(f"  Código     : {codigo}")

    return {
        "sucesso":        True,
        "tipo_pagamento": "boleto",
        "codigo_boleto":  codigo,
        "vencimento":     vencimento,
        "total_pago":     total_reais,
        "mensagem":       "Boleto gerado! Pague até o vencimento.",
    }

def processar_pagamento_pix(total_reais: float) -> dict:
    print("\n── Pagamento por PIX ──")
    chave_pix = "00.000.000/0001-99"
    txid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=26))

    print(f"\n  Chave PIX  : {chave_pix}")
    print(f"  Valor      : {formatar_brl(total_reais)}")
    print(f"  TXID       : {txid}")
    print("  Confirmação em até 5 minutos após o pagamento.")

    return {
        "sucesso":        True,
        "tipo_pagamento": "pix",
        "chave_pix":      chave_pix,
        "txid":           txid,
        "total_pago":     total_reais,
        "mensagem":       "PIX gerado! Pague pelo app do seu banco.",
    }

# ── CONFIRMAR PEDIDO: retorna JSON ──────────────

def confirmar_pedido_json(usuario: dict,
                          ingresso: dict,
                          resultado: dict,
                          quantidade: int,
                          total_valor: float) -> str:
    """
    Monta e retorna o JSON de confirmação do pedido.
    Esse JSON pode ser exibido ao usuário ou enviado ao front-end.
    """
    confirmacao = {
        "status":      "confirmado",
        "usuario": {
            "Usuario_ID": usuario["Usuario_ID"],
            "Nome":       usuario["Nome"],
            "Email":      usuario["Email"],
        },
        "ingresso": {
            "Ingresso_ID":   ingresso["Ingresso_ID"],
            "Ingresso_Nome": ingresso["Ingresso_Nome"],
            "Ingresso_Data": str(ingresso["Ingresso_Data"]),
        },
        "pagamento": {
            "Pedido_Tipo_Pag":      resultado["tipo_pagamento"],
            "Pedido_QNT_Ingressos": quantidade,
            "Pedido_Valor":         total_valor,
            "Pedido_Valor_BRL":     formatar_brl(total_valor),
        },
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Adiciona campos extras dependendo do método
    if resultado["tipo_pagamento"] == "boleto":
        confirmacao["pagamento"]["codigo_boleto"] = resultado["codigo_boleto"]
        confirmacao["pagamento"]["vencimento"]    = resultado["vencimento"]
    elif resultado["tipo_pagamento"] == "pix":
        confirmacao["pagamento"]["chave_pix"] = resultado["chave_pix"]
        confirmacao["pagamento"]["txid"]      = resultado["txid"]
    elif resultado["tipo_pagamento"] == "credito":
        confirmacao["pagamento"]["parcelas"] = resultado["parcelas"]

    return json.dumps(confirmacao, ensure_ascii=False, indent=2)

def json_envio(usuario: dict, 
               ingresso: dict, 
               resultado: dict, 
               quantidade: int, 
               total_valor: float) -> str:

    json_processamento = {
        "operacao": "Cadastro",
        "usuario_id": usuario["Usuario_ID"],
        "ingresso_id": ingresso["Ingresso_ID"],
        "tipo_pagamento": resultado["tipo_pagamento"],
        "quantidade": quantidade,
        "valor_total": total_valor
    }

    return json.dumps(json_processamento, ensure_ascii=False, indent=1)

# ── FLUXO PRINCIPAL DE CHECKOUT ─────────────────

def realizar_checkout(db, cursor):
    print("\n╔══════════════════════════════╗")
    print("║      CHECKOUT DE INGRESSO    ║")
    print("╚══════════════════════════════╝")

    # 1. Entrada
    usuario_id  = int(input("ID do usuário  : "))
    ingresso_id = int(input("ID do ingresso : "))
    quantidade  = int(input("Quantidade     : "))

    # 2. Leitura do banco (somente SELECT)
    usuario  = buscar_usuario(cursor, usuario_id)
    ingresso = buscar_ingresso(cursor, ingresso_id)

    if not usuario:
        print("✗ Usuário não encontrado.")
        return
    if not ingresso:
        print("✗ Ingresso não encontrado.")
        return
    if ingresso["Ingresso_Quantidade"] < quantidade:
        print(f"✗ Estoque insuficiente! Disponível: {ingresso['Ingresso_Quantidade']}")
        return

    # 3. Cálculo do total (Ingresso_Valor está em reais - float)
    subtotal     = float(ingresso["Ingresso_Valor"]) * quantidade   # reais
    taxa         = subtotal * 0.10                                   # 10% taxa de serviço
    total        = subtotal + taxa

    print(f"""
  ┌─ Resumo do Pedido ──────────────────────────┐
  │ Comprador  : {usuario['Nome']}
  │ Evento     : {ingresso['Ingresso_Nome']}
  │ Data       : {ingresso['Ingresso_Data']}
    │ Quantidade : {quantidade}x {formatar_brl(ingresso['Ingresso_Valor'])}
    │ Subtotal   : {formatar_brl(subtotal)}
    │ Taxa (10%) : {formatar_brl(taxa)}
    │ TOTAL      : {formatar_brl(total)}
  └─────────────────────────────────────────────┘""")

    # 4. Forma de pagamento
    print("\nFormas de pagamento:")
    print("  1 - Cartão de Crédito")
    print("  2 - Boleto Bancário")
    print("  3 - PIX")
    opcao = input("Escolha (1/2/3): ").strip()

    mapa_opcao = {"1": "credito", "2": "boleto", "3": "pix"}
    if opcao not in mapa_opcao:
        print("✗ Opção inválida.")
        return

    tipo_pagamento = mapa_opcao[opcao]

    # 5. Processamento do pagamento
    processadores = {
        "credito": processar_pagamento_credito,
        "boleto":  processar_pagamento_boleto,
        "pix":     processar_pagamento_pix,
    }
    resultado = processadores[tipo_pagamento](total)

    if not resultado["sucesso"]:
        print(f"\n✗ Pagamento recusado: {resultado['mensagem']}")
        return

    # 7. Gerar e exibir JSON de confirmação
    try:
        json_confirmacao = confirmar_pedido_json(
            usuario,
            ingresso,
            resultado,
            quantidade,
            total
        )

        json_processamento = json_envio(
            usuario,
            ingresso,
            resultado,
            quantidade,
            total
        )

        print("\n✓ PEDIDO CONFIRMADO — JSON de confirmação:\n")
        print(json_confirmacao)
        print(json_processamento)

        return json_confirmacao

    except mysql.connector.Error as e:
        db.rollback()
        print(f"\n✗ Erro no banco de dados: {e}")
        return None

# ── PONTO DE ENTRADA ────────────────────────────

if __name__ == "__main__":
    
    print("\nO que deseja fazer?")
    print("  1 - Realizar checkout interativo")
    print("  2 - Ver pedidos de um usuário")
    print("  3 - Executar listener SQS para fila de Pedidos (processa apenas 'Cadastro')")
    opcao = input("Opção: ").strip()

    if opcao == "1":
        realizar_checkout(db, cursor)
    elif opcao == "2":
        uid = int(input("ID do usuário: "))
        listar_pedidos_usuario(cursor, uid)
    elif opcao == "3":
        if not sqs_url_entrada:
            print("URL da fila de Pedidos é obrigatória.")
        else:
            sqs = boto3.client("sqs", region_name=region)

            def parse_sqs_body(body):
                if isinstance(body, str):
                    try:
                        return json.loads(body)
                    except json.JSONDecodeError:
                        return None
                if isinstance(body, dict):
                    return body
                return None

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
                payload = parse_sqs_body(body)
                return payload, receipt_handle

            def delete_sqs_message(queue_url, receipt_handle):
                if not receipt_handle:
                    return
                try:
                    sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
                except (BotoCoreError, ClientError) as err:
                    print(f"Erro ao excluir mensagem SQS: {err}")

            def send_sqs_message(queue_url, message_body):
                if not queue_url:
                    return
                try:
                    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body, ensure_ascii=False))
                except (BotoCoreError, ClientError) as err:
                    print(f"Erro ao enviar mensagem SQS: {err}")

            def process_pedido_message(payload):
                # Espera payload com campos: operacao='Cadastro', usuario_id, ingresso_id, quantidade, tipo_pagamento, valor_total
                if not payload:
                    return False
                oper = payload.get("operacao")
                if oper != "Cadastro":
                    print(f"Ignorando operacao de pedido: {oper}")
                    return False

                usuario_id = payload.get("usuario_id")
                ingresso_id = payload.get("ingresso_id")
                quantidade = int(payload.get("quantidade", 0))
                tipo_pagamento = payload.get("tipo_pagamento")
                try:
                    valor_total = float(payload.get("valor_total", 0))
                except Exception:
                    valor_total = 0.0

                if not all([usuario_id, ingresso_id, quantidade, tipo_pagamento, valor_total]):
                    print("Payload de pedido incompleto. Pulando.")
                    return False

                usuario = buscar_usuario(cursor, int(usuario_id))
                ingresso = buscar_ingresso(cursor, int(ingresso_id))

                if not usuario:
                    print("Usuário do pedido não encontrado. Pulando.")
                    return False
                if not ingresso:
                    print("Ingresso do pedido não encontrado. Pulando.")
                    return False
                if ingresso["Ingresso_Quantidade"] < quantidade:
                    print("Estoque insuficiente para o pedido. Pulando.")
                    return False

                resultado = {
                    "sucesso": True,
                    "tipo_pagamento": tipo_pagamento,
                    "total_pago": valor_total
                }

                json_confirmacao = confirmar_pedido_json(usuario, ingresso, resultado, quantidade, valor_total)
                json_processamento = json_envio(usuario, ingresso, resultado, quantidade, valor_total)
                print("Pedido processado e confirmado:")
                print(json_confirmacao)

                # Envia confirmação para fila de saída, se configurada
                if sqs_url_saida:
                    try:
                        send_sqs_message(sqs_url_saida, json.loads(json_processamento))
                    except Exception as e:
                        print(f"Falha ao enviar confirmacao SQS: {e}")

                return True

            print("Iniciando listener SQS para Pedidos. Ctrl+C para parar.")
            try:
                while True:
                    payload, receipt = receive_sqs_message(sqs_url_entrada)
                    if not payload:
                        time.sleep(2)
                        continue
                    processed = process_pedido_message(payload)
                    if processed:
                        delete_sqs_message(sqs_url_entrada, receipt)
            except KeyboardInterrupt:
                print("Listener SQS interrompido pelo usuário.")

    else:
        print("Opção inválida.")

    cursor.close()
    db.close()
