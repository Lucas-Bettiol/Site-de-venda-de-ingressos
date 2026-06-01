import mysql.connector
from datetime import datetime, timedelta
import random
import string
import json

# ──────────────────────────────────────────────
#  BANCO: DB_Ingressos  (schema do SQL entregue)
#
#  Tabelas e colunas reais:
#  Usuarios  → Usuario_ID, Ususario_Nome, Usuario_Email, Usuario_Senha, Usuario_Admin
#  Ingressos → Ingresso_ID, Ingresso_Nome, Ingresso_Data, Ingresso_Valor, Ingresso_Quantidade
#  Pedidos   → Pedido_ID, Usuario_ID, Ingresso_ID, Pedido_Tipo_Pag,
#               Pedido_QNT_Ingressos, Pedido_Valor
#
#  REGRAS:
#  • Leitura: SELECT em Usuarios e Ingressos (sem UPDATE, sem DELETE)
#  • Escrita : apenas INSERT em Pedidos
#  • Ingresso_Valor é INT (centavos) → convertido para reais na exibição
# ──────────────────────────────────────────────

# ── CONEXÃO ────────────────────────────────────

def conectar_banco():
    print("Configure a conexão com o banco de dados MySQL")
    host     = input("Host: ")
    user     = input("User: ")
    password = input("Password: ")
    database = input("Database (padrão DB_Ingressos): ") or "DB_Ingressos"

    db = mysql.connector.connect(
        host=host,
        user=user,
        password=password,
        database=database
    )
    return db

# ── HELPERS ────────────────────────────────────

def formatar_brl(centavos: int) -> str:
    """Recebe valor em centavos (INT do banco) e retorna string formatada."""
    reais = centavos / 100
    return f"R$ {reais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def gerar_codigo_pedido() -> str:
    sufixo = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"PED-{sufixo}"

# ── LEITURA DO BANCO (somente SELECT) ──────────

def buscar_usuario(cursor, usuario_id: int) -> dict | None:
    cursor.execute(
        """SELECT Usuario_ID, Ususario_Nome, Usuario_Email
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
        "Ingresso_Data":      row[2],           # objeto date do MySQL
        "Ingresso_Valor":     row[3],           # INT em centavos
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

def processar_pagamento_credito(total_centavos: int) -> dict:
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

    parcela_centavos = total_centavos // parcelas
    print(f"\n  {parcelas}x de {formatar_brl(parcela_centavos)} — Total: {formatar_brl(total_centavos)}")

    # Ponto de integração com gateway (Stripe, Cielo, PagSeguro, etc.)
    # response = gateway.charge(numero, cvv, validade, total_centavos)

    return {
        "sucesso":        True,
        "tipo_pagamento": "credito",
        "parcelas":       parcelas,
        "total_pago":     total_centavos,
        "mensagem":       "Pagamento no crédito aprovado!",
    }

def processar_pagamento_boleto(total_centavos: int) -> dict:
    print("\n── Pagamento por Boleto Bancário ──")
    vencimento = (datetime.now() + timedelta(days=2)).strftime("%d/%m/%Y")

    def _seg():
        return ''.join(random.choices(string.digits, k=5))

    codigo = (
        f"34191.{_seg()} {_seg()}.{_seg()}0 "
        f"{_seg()}.{_seg()}0 1 {str(total_centavos).zfill(14)}"
    )

    print(f"\n  Vencimento : {vencimento}")
    print(f"  Valor      : {formatar_brl(total_centavos)}")
    print(f"  Código     : {codigo}")

    return {
        "sucesso":        True,
        "tipo_pagamento": "boleto",
        "codigo_boleto":  codigo,
        "vencimento":     vencimento,
        "total_pago":     total_centavos,
        "mensagem":       "Boleto gerado! Pague até o vencimento.",
    }

def processar_pagamento_pix(total_centavos: int) -> dict:
    print("\n── Pagamento por PIX ──")
    chave_pix = "00.000.000/0001-99"   # substitua pela chave real da empresa
    txid = ''.join(random.choices(string.ascii_uppercase + string.digits, k=26))

    print(f"\n  Chave PIX  : {chave_pix}")
    print(f"  Valor      : {formatar_brl(total_centavos)}")
    print(f"  TXID       : {txid}")
    print("  Confirmação em até 5 minutos após o pagamento.")

    return {
        "sucesso":        True,
        "tipo_pagamento": "pix",
        "chave_pix":      chave_pix,
        "txid":           txid,
        "total_pago":     total_centavos,
        "mensagem":       "PIX gerado! Pague pelo app do seu banco.",
    }

# ── INSERT EM PEDIDOS (única escrita no banco) ──

def registrar_pedido(db, cursor,
                     usuario_id: int,
                     ingresso_id: int,
                     tipo_pagamento: str,
                     quantidade: int,
                     total_centavos: int) -> int:
    """
    Insere apenas em Pedidos.
    NÃO altera Ingressos nem Usuarios.
    Retorna o Pedido_ID gerado.
    """
    sql = """
        INSERT INTO Pedidos
            (Usuario_ID, Ingresso_ID, Pedido_Tipo_Pag, Pedido_QNT_Ingressos, Pedido_Valor)
        VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(sql, (usuario_id, ingresso_id, tipo_pagamento, quantidade, total_centavos))
    db.commit()
    return cursor.lastrowid

# ── CONFIRMAR PEDIDO: retorna JSON ──────────────

def confirmar_pedido_json(pedido_id: int,
                          usuario: dict,
                          ingresso: dict,
                          resultado: dict,
                          quantidade: int,
                          total_centavos: int) -> str:
    """
    Monta e retorna o JSON de confirmação do pedido.
    Esse JSON pode ser exibido ao usuário ou enviado ao front-end.
    """
    confirmacao = {
        "status":      "confirmado",
        "Pedido_ID":   pedido_id,
        "codigo":      gerar_codigo_pedido(),
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
            "Pedido_Valor":         total_centavos,
            "Pedido_Valor_BRL":     formatar_brl(total_centavos),
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

    # 3. Cálculo do total (Ingresso_Valor já está em centavos)
    subtotal     = ingresso["Ingresso_Valor"] * quantidade   # centavos
    taxa         = int(subtotal * 0.10)                       # 10% taxa de serviço
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

    # 6. INSERT em Pedidos (único ponto de escrita)
    try:
        pedido_id = registrar_pedido(
            db, cursor,
            usuario_id, ingresso_id,
            tipo_pagamento, quantidade,
            total
        )

        # 7. Gerar e exibir JSON de confirmação
        json_confirmacao = confirmar_pedido_json(
            pedido_id, usuario, ingresso,
            resultado, quantidade, total
        )

        print("\n✓ PEDIDO CONFIRMADO — JSON de confirmação:\n")
        print(json_confirmacao)

        return json_confirmacao

    except mysql.connector.Error as e:
        db.rollback()
        print(f"\n✗ Erro no banco de dados: {e}")
        return None

# ── PONTO DE ENTRADA ────────────────────────────

if __name__ == "__main__":
    db     = conectar_banco()
    cursor = db.cursor()

    print("\nO que deseja fazer?")
    print("  1 - Realizar checkout")
    print("  2 - Ver pedidos de um usuário")
    opcao = input("Opção: ").strip()

    if opcao == "1":
        realizar_checkout(db, cursor)
    elif opcao == "2":
        uid = int(input("ID do usuário: "))
        listar_pedidos_usuario(cursor, uid)
    else:
        print("Opção inválida.")

    cursor.close()
    db.close()
