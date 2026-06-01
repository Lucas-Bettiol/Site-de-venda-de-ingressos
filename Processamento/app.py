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

