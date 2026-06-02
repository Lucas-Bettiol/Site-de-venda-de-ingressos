from ast import While

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

    sql = "INSERT INTO Usuarios (Usuario_Nome, Usuario_Email, Usuario_Senha, Usuario_Admin) VALUES (%s, %s, %s, %s);"
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

    sql = "INSERT INTO Ingressos (Ingresso_Nome, Ingresso_Data, Ingresso_Valor, Ingresso_Quantidade) VALUES (%s, %s, %s, %s)"
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
    valor_total = input("Valor Total: ")

    sql = "INSERT INTO Pedidos (Usuario_ID, Ingresso_ID, Pedido_Tipo_Pag, Pedido_QNT_Ingressos, Pedido_Valor) VALUES (%s, %s, %s, %s, %s)"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade, valor_total)
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

    sql = "UPDATE Usuarios SET Usuario_Nome = %s, Usuario_Email = %s, Usuario_Senha = %s, Usuario_Admin = %s WHERE Usuario_ID = %s"
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

    sql = "UPDATE Ingressos SET Ingresso_Nome = %s, Ingresso_Data = %s, Ingresso_Valor = %s, Ingresso_Quantidade = %s WHERE Ingresso_ID = %s"
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
    valor_total = input("Novo Valor Total: ")

    sql = "UPDATE Pedidos SET Usuario_ID = %s, Ingresso_ID = %s, Pedido_Tipo_Pag = %s, Pedido_QNT_Ingressos = %s, Pedido_Valor = %s WHERE Pedido_ID = %s"
    val = (id_usuario, id_ingresso, tipo_pagamento, quantidade, valor_total, id_pedido)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido editado com sucesso!")

# Criação das funções de exclusão

def excluir_usuario():
    print("Exclusão de Usuário")
    id_usuario = input("ID do Usuário a ser excluído: ")

    sql = "DELETE FROM Usuarios WHERE Usuario_ID = %s"
    val = (id_usuario,)
    cursor.execute(sql, val)
    db.commit()
    print("Usuário excluído com sucesso!")

def excluir_ingresso():
    print("Exclusão de Ingresso")
    id_ingresso = input("ID do Ingresso a ser excluído: ")

    sql = "DELETE FROM Ingressos WHERE Ingresso_ID = %s"
    val = (id_ingresso,)
    cursor.execute(sql, val)
    db.commit()
    print("Ingresso excluído com sucesso!")

def excluir_pedido():
    print("Exclusão de Pedido")
    id_pedido = input("ID do Pedido a ser excluído: ")

    sql = "DELETE FROM Pedidos WHERE Pedido_ID = %s"
    val = (id_pedido,)
    cursor.execute(sql, val)
    db.commit()
    print("Pedido excluído com sucesso!")

# Funções para uso administrativo

def resetar_contador_id():
    print("Resetar Contador de IDs")
    tabela = input("Tabela (Usuarios / Ingressos / Pedidos): ")

    sql = (f"ALTER TABLE {tabela} AUTO_INCREMENT = 0")
    cursor.execute(sql)
    db.commit()
    print(f"Contador de IDs da tabela {tabela} resetado com sucesso!")

def mostrar_tabela():
    print("Mostrar Tabela")
    tabela = input("Tabela (Usuarios / Ingressos / Pedidos): ")

    sql = (f"SELECT * FROM {tabela}")
    cursor.execute(sql)
    resultados = cursor.fetchall()
    for resultado in resultados:
        print(resultado)

# Criação de uma função para exibir o menu

def menu():
    print("Menu:")
    print("1. Cadastros")
    print("2. Edições")
    print("3. Exclusões")
    print("4. Resetar Contador de IDs")
    print("5. Mostrar Tabela")
    print("6. Sair")
    escolha = input("Escolha uma opção: ")
    if escolha == "1":
        print("1. Cadastrar Usuário")
        print("2. Cadastrar Ingresso")
        print("3. Cadastrar Pedido")
        escolha_cadastro = input("Escolha uma opção: ")
        if escolha_cadastro == "1":
            cadastrar_usuario()
        elif escolha_cadastro == "2":
            cadastrar_ingresso()
        elif escolha_cadastro == "3":
            cadastrar_pedido()
    elif escolha == "2":
        print("1. Editar Usuário")
        print("2. Editar Ingresso")
        print("3. Editar Pedido")
        escolha_edicao = input("Escolha uma opção: ")
        if escolha_edicao == "1":
            editar_usuario()
        elif escolha_edicao == "2":
            editar_ingresso()
        elif escolha_edicao == "3":
            editar_pedido()
    elif escolha == "3":
        print("1. Excluir Usuário")
        print("2. Excluir Ingresso")
        print("3. Excluir Pedido")
        escolha_exclusao = input("Escolha uma opção: ")
        if escolha_exclusao == "1":
            excluir_usuario()
        elif escolha_exclusao == "2":
            excluir_ingresso()
        elif escolha_exclusao == "3":
            excluir_pedido()
    elif escolha == "4":
        resetar_contador_id()
    elif escolha == "5":
        mostrar_tabela()
    elif escolha == "6":
        print("Saindo...")
        exit()

while True:
    menu()
