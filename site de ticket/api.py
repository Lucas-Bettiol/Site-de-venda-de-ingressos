import json
import os

import boto3
import mysql.connector
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from mysql.connector import Error as MySQLError

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path="")
CORS(app)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "DB_Ingressos"),
}

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
SQS_URLS = {
    "usuarios": os.getenv("SQS_URL_USUARIOS", ""),
    "ingressos": os.getenv("SQS_URL_INGRESSOS", ""),
    "pedidos": os.getenv("SQS_URL_PEDIDOS", ""),
}

EVENT_EMOJIS = ["🎸", "🎤", "🎷", "🎌", "🌟", "🎭", "🎫", "🎪", "🎬", "⚽"]
_USUARIO_NOME_COL = None


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def get_sqs():
    return boto3.client("sqs", region_name=AWS_REGION)


def emoji_for_event(nome: str, event_id: int) -> str:
    return EVENT_EMOJIS[event_id % len(EVENT_EMOJIS)]


def normalize_pagamento(tipo: str) -> str:
    return (tipo or "").strip().lower()


def map_usuario(row) -> dict:
    return {
        "id_usuario": row[0],
        "nome": row[1],
        "email": row[2],
        "tipo": int(row[4]) if row[4] is not None else 0,
    }


def map_ingresso(row) -> dict:
    valor = row[3]
    if valor is not None:
        valor = float(valor)
    return {
        "id_ingresso": row[0],
        "nome": row[1],
        "data": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
        "preco": valor,
        "quantidade": int(row[4]),
        "emoji": emoji_for_event(row[1], row[0]),
    }


def map_pedido(row) -> dict:
    return {
        "id_pedido": row[0],
        "id_usuario": row[1],
        "id_ingresso": row[2],
        "tipo_pagamento": row[3],
        "quantidade": int(row[4]),
        "valor_total": float(row[5]) if row[5] is not None else 0,
        "usuario_nome": row[6] or "Desconhecido",
        "ingresso_nome": row[7] or "Desconhecido",
        "ingresso_preco": float(row[8]) if row[8] is not None else 0,
        "ingresso_emoji": emoji_for_event(row[7] or "", row[2] or 0),
        "status": "aprovado",
        "data_pedido": None,
    }


def usuario_nome_column():
    """Detecta Usuario_Nome (app.py) ou Ususario_Nome (dump SQL)."""
    global _USUARIO_NOME_COL
    if _USUARIO_NOME_COL:
        return _USUARIO_NOME_COL

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM Usuarios")
    columns = {row[0] for row in cur.fetchall()}
    cur.close()
    conn.close()

    if "Usuario_Nome" in columns:
        _USUARIO_NOME_COL = "Usuario_Nome"
    elif "Ususario_Nome" in columns:
        _USUARIO_NOME_COL = "Ususario_Nome"
    else:
        raise RuntimeError("Coluna de nome não encontrada na tabela Usuarios.")

    return _USUARIO_NOME_COL


def usuario_select_sql():
    col = usuario_nome_column()
    return f"""
        SELECT Usuario_ID, {col}, Usuario_Email, Usuario_Senha, Usuario_Admin
        FROM Usuarios
    """


def send_sqs(queue_key: str, payload: dict) -> tuple[bool, str]:
    queue_url = SQS_URLS.get(queue_key, "")
    if not queue_url:
        return False, f"URL da fila SQS '{queue_key}' não configurada."

    try:
        sqs = get_sqs()
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload, ensure_ascii=False),
        )
        return True, "Mensagem enviada para a fila SQS."
    except (BotoCoreError, ClientError) as err:
        return False, f"Erro ao enviar para SQS: {err}"


def api_error(message, status=400):
    return jsonify({"ok": False, "error": message}), status


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/health")
def health():
    db_ok = False
    db_error = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        db_ok = True
    except MySQLError as err:
        db_error = str(err)

    return jsonify({
        "ok": db_ok,
        "database": "connected" if db_ok else "error",
        "database_error": db_error,
        "sqs": {
            "usuarios": bool(SQS_URLS["usuarios"]),
            "ingressos": bool(SQS_URLS["ingressos"]),
            "pedidos": bool(SQS_URLS["pedidos"]),
        },
    })


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    senha = data.get("senha") or ""

    if not email or not senha:
        return api_error("E-mail e senha são obrigatórios.", 400)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            usuario_select_sql() + " WHERE Usuario_Email = %s",
            (email,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro no banco de dados: {err}", 500)

    if not row or row[3] != senha:
        return api_error("E-mail ou senha incorretos.", 401)

    user = map_usuario(row)
    return jsonify({"ok": True, "user": user})


@app.route("/api/ingressos")
def list_ingressos():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """SELECT Ingresso_ID, Ingresso_Nome, Ingresso_Data,
                      Ingresso_Valor, Ingresso_Quantidade
               FROM Ingressos
               ORDER BY Ingresso_Data ASC"""
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao listar ingressos: {err}", 500)

    return jsonify({"ok": True, "ingressos": [map_ingresso(r) for r in rows]})


@app.route("/api/ingressos/<int:ingresso_id>")
def get_ingresso(ingresso_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """SELECT Ingresso_ID, Ingresso_Nome, Ingresso_Data,
                      Ingresso_Valor, Ingresso_Quantidade
               FROM Ingressos WHERE Ingresso_ID = %s""",
            (ingresso_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao buscar ingresso: {err}", 500)

    if not row:
        return api_error("Ingresso não encontrado.", 404)

    return jsonify({"ok": True, "ingresso": map_ingresso(row)})


@app.route("/api/usuarios")
def list_usuarios():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            usuario_select_sql() + " ORDER BY Usuario_ID ASC"
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao listar usuários: {err}", 500)

    return jsonify({"ok": True, "usuarios": [map_usuario(r) for r in rows]})


@app.route("/api/pedidos")
def list_pedidos():
    try:
        conn = get_db()
        cur = conn.cursor()
        nome_col = usuario_nome_column()
        cur.execute(
            f"""SELECT p.Pedido_ID, p.Usuario_ID, p.Ingresso_ID,
                      p.Pedido_Tipo_Pag, p.Pedido_QNT_Ingressos, p.Pedido_Valor,
                      u.{nome_col}, i.Ingresso_Nome, i.Ingresso_Valor
               FROM Pedidos p
               JOIN Usuarios u ON p.Usuario_ID = u.Usuario_ID
               JOIN Ingressos i ON p.Ingresso_ID = i.Ingresso_ID
               ORDER BY p.Pedido_ID DESC"""
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao listar pedidos: {err}", 500)

    return jsonify({"ok": True, "pedidos": [map_pedido(r) for r in rows]})


@app.route("/api/pedidos/usuario/<int:usuario_id>")
def pedidos_usuario(usuario_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        nome_col = usuario_nome_column()
        cur.execute(
            f"""SELECT p.Pedido_ID, p.Usuario_ID, p.Ingresso_ID,
                      p.Pedido_Tipo_Pag, p.Pedido_QNT_Ingressos, p.Pedido_Valor,
                      u.{nome_col}, i.Ingresso_Nome, i.Ingresso_Valor
               FROM Pedidos p
               JOIN Usuarios u ON p.Usuario_ID = u.Usuario_ID
               JOIN Ingressos i ON p.Ingresso_ID = i.Ingresso_ID
               WHERE p.Usuario_ID = %s
               ORDER BY p.Pedido_ID DESC""",
            (usuario_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao listar pedidos do usuário: {err}", 500)

    return jsonify({"ok": True, "pedidos": [map_pedido(r) for r in rows]})


@app.route("/api/stats")
def stats():
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM Usuarios")
        total_usuarios = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM Ingressos")
        total_ingressos = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM Pedidos")
        total_pedidos = cur.fetchone()[0]

        cur.execute(
            """SELECT COALESCE(SUM(p.Pedido_Valor), 0)
               FROM Pedidos p"""
        )
        receita = float(cur.fetchone()[0] or 0)

        cur.execute("SELECT COUNT(*) FROM Ingressos WHERE Ingresso_Quantidade > 0")
        ingressos_disponiveis = cur.fetchone()[0]

        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao calcular estatísticas: {err}", 500)

    return jsonify({
        "ok": True,
        "stats": {
            "totalUsuarios": total_usuarios,
            "totalIngressos": total_ingressos,
            "totalPedidos": total_pedidos,
            "pedidosAprovados": total_pedidos,
            "receita": receita,
            "ingressosDisponiveis": ingressos_disponiveis,
        },
    })


@app.route("/api/sqs/pedidos", methods=["POST"])
def sqs_pedido():
    """Envia pedido para fila de pagamento/checkout (formato checkout_ingressos.json_envio)."""
    data = request.get_json(silent=True) or {}

    usuario_id = data.get("usuario_id")
    ingresso_id = data.get("ingresso_id")
    quantidade = data.get("quantidade")
    tipo_pagamento = normalize_pagamento(data.get("tipo_pagamento"))
    valor_total = data.get("valor_total")

    if not all([usuario_id, ingresso_id, quantidade, tipo_pagamento, valor_total]):
        return api_error("Payload incompleto para pedido.", 400)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT Ingresso_Quantidade, Ingresso_Valor FROM Ingressos WHERE Ingresso_ID = %s",
            (ingresso_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
    except MySQLError as err:
        return api_error(f"Erro ao validar estoque: {err}", 500)

    if not row:
        return api_error("Ingresso não encontrado.", 404)
    if int(row[0]) < int(quantidade):
        return api_error(f"Estoque insuficiente. Disponível: {row[0]}", 400)

    payload = {
        "operacao": "Cadastro",
        "usuario_id": int(usuario_id),
        "ingresso_id": int(ingresso_id),
        "tipo_pagamento": tipo_pagamento,
        "quantidade": int(quantidade),
        "valor_total": float(valor_total),
    }

    pagamento = data.get("pagamento")
    if isinstance(pagamento, dict) and pagamento:
        payload["pagamento"] = pagamento

    ok, msg = send_sqs("pedidos", payload)
    if not ok:
        return api_error(msg, 503)

    return jsonify({"ok": True, "message": msg, "payload": payload})


@app.route("/api/sqs/usuarios", methods=["POST"])
def sqs_usuario():
    data = request.get_json(silent=True) or {}
    operacao = data.get("operacao")

    if operacao not in ("Cadastro", "Edicao", "Exclusao"):
        return api_error("Operação inválida. Use Cadastro, Edicao ou Exclusao.", 400)

    payload = {"operacao": operacao}

    if operacao in ("Cadastro", "Edicao"):
        for key in ("nome", "email", "admin"):
            if key not in data:
                return api_error(f"Campo obrigatório ausente: {key}", 400)
        if operacao == "Cadastro" and not data.get("senha"):
            return api_error("senha é obrigatória no cadastro.", 400)

        senha = data.get("senha")
        if operacao == "Edicao" and not senha:
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute(
                    "SELECT Usuario_Senha FROM Usuarios WHERE Usuario_ID = %s",
                    (int(data["usuario_id"]),),
                )
                row = cur.fetchone()
                cur.close()
                conn.close()
                if not row:
                    return api_error("Usuário não encontrado.", 404)
                senha = row[0]
            except MySQLError as err:
                return api_error(f"Erro ao buscar senha: {err}", 500)

        payload.update({
            "nome": data["nome"],
            "email": data["email"],
            "senha": senha,
            "admin": int(data["admin"]),
        })

    if operacao in ("Edicao", "Exclusao"):
        if "usuario_id" not in data:
            return api_error("usuario_id é obrigatório.", 400)
        payload["usuario_id"] = int(data["usuario_id"])

    ok, msg = send_sqs("usuarios", payload)
    if not ok:
        return api_error(msg, 503)

    return jsonify({"ok": True, "message": msg, "payload": payload})


@app.route("/api/sqs/ingressos", methods=["POST"])
def sqs_ingresso():
    data = request.get_json(silent=True) or {}
    operacao = data.get("operacao")

    if operacao not in ("Cadastro", "Edicao", "Exclusao"):
        return api_error("Operação inválida. Use Cadastro, Edicao ou Exclusao.", 400)

    payload = {"operacao": operacao}

    if operacao in ("Cadastro", "Edicao"):
        for key in ("nome", "data", "valor", "quantidade"):
            if key not in data:
                return api_error(f"Campo obrigatório ausente: {key}", 400)
        payload.update({
            "nome": data["nome"],
            "data": data["data"],
            "valor": float(data["valor"]),
            "quantidade": int(data["quantidade"]),
        })

    if operacao in ("Edicao", "Exclusao"):
        if "ingresso_id" not in data:
            return api_error("ingresso_id é obrigatório.", 400)
        payload["ingresso_id"] = int(data["ingresso_id"])

    ok, msg = send_sqs("ingressos", payload)
    if not ok:
        return api_error(msg, 503)

    return jsonify({"ok": True, "message": msg, "payload": payload})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"TicketFlow API em http://localhost:{port}")
    print("Configure DB_* e SQS_URL_* no arquivo .env")
    app.run(host="0.0.0.0", port=port, debug=True)
