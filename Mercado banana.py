
import sqlite3
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

# ==============================
# CONEXÕES COM OS BANCOS
# ==============================

# usuarios SQL
usuarios = sqlite3.connect('usuarios.db')
cursor_usuarios = usuarios.cursor()

# produtos SQL
produtos = sqlite3.connect('produtos.db')
cursor_produtos = produtos.cursor()

# vendas SQL
vendas = sqlite3.connect('vendas.db')
cursor_vendas = vendas.cursor()


# ==============================
# CRIAR TABELAS
# ==============================

cursor_usuarios.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    idade INTEGER NOT NULL,
    senha TEXT NOT NULL
)
""")
usuarios.commit()


cursor_produtos.execute("""
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    valor REAL NOT NULL,
    estoque INTEGER NOT NULL
)
""")
produtos.commit()


cursor_vendas.execute("""
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    produto_id INTEGER NOT NULL,
    quantidade INTEGER NOT NULL,
    valor_unitario REAL NOT NULL
)
""")
vendas.commit()


# ==============================
# PRODUTOS INICIAIS
# ==============================

cursor_produtos.executemany("""
INSERT OR IGNORE INTO produtos (id, nome, valor, estoque)
VALUES (?, ?, ?, ?)
""", [
    (1, 'Banana', 5.00, 50),
    (2, 'Maçã', 7.50, 50),
    (3, 'Arroz', 25.00, 50),
    (4, 'Feijão', 8.00, 50),
    (5, 'Leite', 6.00, 50)
])

produtos.commit()


# ==============================
# CONECTAR OS BANCOS
# ==============================

cursor_vendas.execute(
    "ATTACH DATABASE 'usuarios.db' AS usuarios_db"
)
cursor_vendas.execute(
    "ATTACH DATABASE 'produtos.db' AS db_produtos"
)


carrinho = []
sub_total = 0
id_compra = None


# ==============================
# LOGIN
# ==============================

def login():
    global id_compra

    print('Iniciando sistema de login')

    nome = input('Digite o nome de usuario: ')
    senha = input('Digite sua senha: ')

    cursor_usuarios.execute("""
        SELECT senha, id FROM usuarios
        WHERE nome = ?
    """, (nome,))

    validar = cursor_usuarios.fetchone()

    if validar:
        try:
            ph.verify(validar[0], senha)

            print('Acesso concedido!')
            id_compra = validar[1]
            loja()

        except VerifyMismatchError:
            print('Senha incorreta.')

    else:
        print('Usuario nao encontrado.')
        print('Deseja realizar um cadastro?')
        print('1 - Sim')
        print('2 - Nao')

        try:
            opcao = int(input('Digite sua opcao: '))
        except ValueError:
            print('Digite apenas numeros.')
            return

        if opcao == 1:
            cadastro()


# ==============================
# CADASTRO
# ==============================

def cadastro():
    nome_cad = input('Crie um nome de usuario: ')

    while True:
        try:
            idade = int(input('Digite sua idade: '))
            break
        except ValueError:
            print('Digite apenas numeros nesse campo!')

    senha_cad = input('Digite sua senha: ')
    senha_hash = ph.hash(senha_cad)

    cursor_usuarios.execute("""
        INSERT INTO usuarios (nome, idade, senha)
        VALUES (?, ?, ?)
    """, (nome_cad, idade, senha_hash))

    usuarios.commit()

    print(f'Cadastro realizado com sucesso, {nome_cad}!')
    print('Agora faca login para acessar o sistema.')


# ==============================
# VER PRODUTOS E ADICIONAR AO CARRINHO
# ==============================

def ver_produtos():
    global sub_total

    cursor_produtos.execute("""
        SELECT id, nome, valor, estoque
        FROM produtos
    """)

    resultado = cursor_produtos.fetchall()

    print('\\n====== PRODUTOS ======')

    for produto in resultado:
        print(
            f'{produto[0]}: {produto[1]} - '
            f'R$ {produto[2]:.2f} '
            f'(Estoque: {produto[3]})'
        )

    while True:
        print('\\n0 - Voltar')
        try:
            carrinho_produto = int(
                input('Digite o ID do produto: ')
            )
        except ValueError:
            print('Digite apenas numeros.')
            continue

        if carrinho_produto == 0:
            return

        try:
            carrinho_estoque = int(
                input('Digite a quantidade desejada: ')
            )
        except ValueError:
            print('Digite apenas numeros.')
            continue

        if carrinho_estoque <= 0:
            print('Quantidade invalida.')
            continue

        cursor_produtos.execute("""
            SELECT id, estoque, valor, nome
            FROM produtos
            WHERE id = ?
        """, (carrinho_produto,))

        resultado_produtos = cursor_produtos.fetchone()

        if resultado_produtos is None:
            print('Produto inexistente.')
            continue

        if carrinho_estoque > resultado_produtos[1]:
            print('Estoque insuficiente.')
            continue

        valor_conta = carrinho_estoque * resultado_produtos[2]

        item = {
            'id': carrinho_produto,
            'nome': resultado_produtos[3],
            'valor': resultado_produtos[2],
            'quantidade': carrinho_estoque,
            'total': valor_conta
        }

        carrinho.append(item)
        sub_total += valor_conta

        print(f"{item['nome']} adicionado ao carrinho.")
        print(f'Subtotal: R$ {sub_total:.2f}')


# ==============================
# COMPRAR
# ==============================

def comprar():
    global carrinho, sub_total

    if not carrinho:
        print('Seu carrinho esta vazio.')
        return

    print(f'Total da compra: R$ {sub_total:.2f}')
    print('1 - Confirmar compra')
    print('2 - Cancelar compra')

    try:
        confirmar = int(input('Digite sua opcao: '))
    except ValueError:
        print('Digite apenas numeros.')
        return

    if confirmar == 2:
        carrinho = []
        sub_total = 0
        print('Compra cancelada.')
        return

    if confirmar != 1:
        print('Opcao invalida.')
        return

    try:
        # Verificar novamente o estoque e registrar a venda
        for compra in carrinho:
            cursor_produtos.execute("""
                SELECT estoque
                FROM produtos
                WHERE id = ?
            """, (compra['id'],))

            resultado = cursor_produtos.fetchone()

            if resultado is None or resultado[0] < compra['quantidade']:
                raise ValueError(
                    f"Estoque insuficiente para {compra['nome']}."
                )

        for compra in carrinho:
            cursor_vendas.execute("""
                INSERT INTO vendas
                    (client_id, produto_id, quantidade, valor_unitario)
                VALUES (?, ?, ?, ?)
            """, (
                id_compra,
                compra['id'],
                compra['quantidade'],
                compra['valor']
            ))

            cursor_produtos.execute("""
                UPDATE produtos
                SET estoque = estoque - ?
                WHERE id = ?
            """, (compra['quantidade'], compra['id']))

        vendas.commit()
        produtos.commit()

        print('Compra registrada com sucesso!')

        carrinho = []
        sub_total = 0

    except (ValueError, sqlite3.Error) as erro:
        vendas.rollback()
        produtos.rollback()
        print(f'Nao foi possivel concluir a compra: {erro}')


# ==============================
# VER CARRINHO
# ==============================

def ver_carrinho():
    if not carrinho:
        print('Seu carrinho esta vazio.')
        return

    for item in carrinho:
        print(
            f"{item['nome']} | "
            f"Quantidade: {item['quantidade']} | "
            f"Total: R$ {item['total']:.2f}"
        )

    print(f'Subtotal: R$ {sub_total:.2f}')


# ==============================
# HISTORICO DE COMPRAS
# ==============================

def visualizar_compras():
    cursor_vendas.execute("""
        SELECT
            usuarios_db.usuarios.id,
            usuarios_db.usuarios.nome,
            db_produtos.produtos.nome,
            vendas.quantidade,
            vendas.valor_unitario
        FROM vendas
        JOIN usuarios_db.usuarios
            ON usuarios_db.usuarios.id = vendas.client_id
        JOIN db_produtos.produtos
            ON db_produtos.produtos.id = vendas.produto_id
        WHERE usuarios_db.usuarios.id = ?
    """, (id_compra,))

    compras = cursor_vendas.fetchall()

    if not compras:
        print('Nenhuma compra encontrada.')
        return

    print('\\n===== HISTORICO DE COMPRAS =====')

    for mostrar in compras:
        print(f'''
ID do cliente: {mostrar[0]}
Nome do cliente: {mostrar[1]}
Produto: {mostrar[2]}
Quantidade: {mostrar[3]}
Valor unitario: R$ {mostrar[4]:.2f}
----------------------------
''')


# ==============================
# SAIR DA LOJA
# ==============================

def sair():
    return


# ==============================
# MENU DA LOJA
# ==============================

def loja():
    while True:
        print('\\n===== MERCADO BANANA =====')
        print('1 - Ver produtos')
        print('2 - Comprar')
        print('3 - Ver carrinho')
        print('4 - Visualizar compras')
        print('5 - Sair')

        try:
            option_menu = int(
                input('Digite a opcao desejada: ')
            )
        except ValueError:
            print('Digite apenas numeros!')
            continue

        if option_menu == 1:
            ver_produtos()

        elif option_menu == 2:
            comprar()

        elif option_menu == 3:
            ver_carrinho()

        elif option_menu == 4:
            visualizar_compras()

        elif option_menu == 5:
            return

        else:
            print('Opcao invalida.')


# ==============================
# MENU PRINCIPAL
# ==============================

try:
    while True:
        print('\\n==============================')
        print('         MERCADINHO')
        print('      Sistema de Login')
        print('==============================')
        print('[1] Login')
        print('[2] Cadastro')
        print('[3] Sair')

        try:
            opcao = int(input('Escolha uma opcao: '))
        except ValueError:
            print('Digite apenas numeros!')
            continue

        if opcao == 1:
            login()

        elif opcao == 2:
            cadastro()

        elif opcao == 3:
            break

        else:
            print('Opcao invalida.')

finally:
    usuarios.close()
    produtos.close()
    vendas.close()

