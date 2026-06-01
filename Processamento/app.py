import mysql.connector

# Configurações de conexão com o banco de dados
print("Configure a conexão com o banco de dados MySQL")
host = input("Host: ")
user = input("User: ")
password = input("Password: ")
database = input("Database: ")

# Conexão com o banco de dados
db = mysql.connector.connect(
    host=host,
    user=user,
    password=password,
    database=database
)

cursor = db.cursor()

# Criação das funções de cadastro

def cadastrar_usuario():
    print("Cadastro de Usuário")
    nome = input("Nome: ")
    email = input("Email: ")
    senha = input("Senha: ")
    tipo = input("Tipo (admin 1/usuario 0): ")

    sql = "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (%s, %s, %s, %s)"
    val = (nome, email, senha, tipo)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário cadastrado com sucesso!")

def cadastrar_ingresso():
    print("Cadastro de Ingresso")
    nome = input("Nome do Evento: ")
    data = input("Data do Evento (YYYY-MM-DD): ")
    valor = input("Preço: ")
    quantidade = input("Quantidade: ")

    sql = "INSERT INTO ingressos (nome, data, preco, quantidade) VALUES (%s, %s, %s, %s)"
    val = (nome, data, valor, quantidade)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso cadastrado com sucesso!")

def cadastrar_pedido():
    print("Cadastro de Pedido")
    id_usuario = input("ID do Usuário: ")
    id_ingresso = input("ID do Ingresso: ")
    tipo_pagamento = input("Tipo de Pagamento (credido/boleto/PIX): ")
    quantidade = input("Quantidade: ")

    sql = "INSERT INTO pedidos (id_usuario, id_ingresso, tipo_pagamento, quantidade) VALUES (%s, %s, %s, %s)"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido cadastrado com sucesso!")

# Criação das funções de edição

def editar_usuario():
    print("Edição de Usuário")
    id_usuario = input("ID do Usuário a ser editado: ")
    nome = input("Novo Nome: ")
    email = input("Novo Email: ")
    senha = input("Nova Senha: ")
    tipo = input("Novo Tipo (admin 1/usuario 0): ")

    sql = "UPDATE usuarios SET nome = %s, email = %s, senha = %s, tipo = %s WHERE id_usuario = %s"
    val = (nome, email, senha, tipo, id_usuario)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário editado com sucesso!")

def editar_ingresso():
    print("Edição de Ingresso")
    id_ingresso = input("ID do Ingresso a ser editado: ")
    nome = input("Novo Nome do Evento: ")
    data = input("Nova Data do Evento (YYYY-MM-DD): ")
    valor = input("Novo Preço: ")
    quantidade = input("Nova Quantidade: ")

    sql = "UPDATE ingressos SET nome = %s, data = %s, preco = %s, quantidade = %s WHERE id_ingresso = %s"
    val = (nome, data, valor, quantidade, id_ingresso)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso editado com sucesso!")

def editar_pedido():
    print("Edição de Pedido")
    id_pedido = input("ID do Pedido a ser editado: ")
    id_usuario = input("Novo ID do Usuário: ")
    id_ingresso = input("Novo ID do Ingresso: ")
    tipo_pagamento = input("Novo Tipo de Pagamento (credido/boleto/PIX): ")
    quantidade = input("Nova Quantidade: ")

    sql = "UPDATE pedidos SET id_usuario = %s, id_ingresso = %s, tipo_pagamento = %s, quantidade = %s WHERE id_pedido = %s"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade, id_pedido)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido editado com sucesso!")

# Criação das funções de exclusão

def excluir_usuario():
    print("Exclusão de Usuário")
    id_usuario = input("ID do Usuário a ser excluído: ")

    sql = "DELETE FROM usuarios WHERE id_usuario = %s"
    val = (id_usuario,)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário excluído com sucesso!")

def excluir_ingresso():
    print("Exclusão de Ingresso")
    id_ingresso = input("ID do Ingresso a ser excluído: ")

    sql = "DELETE FROM ingressos WHERE id_ingresso = %s"
    val = (id_ingresso,)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso excluído com sucesso!")

def excluir_pedido():
    print("Exclusão de Pedido")
    id_pedido = input("ID do Pedido a ser excluído: ")

    sql = "DELETE FROM pedidos WHERE id_pedido = %s"
    val = (id_pedido,)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido excluído com sucesso!")