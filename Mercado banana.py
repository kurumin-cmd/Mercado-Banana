
import sqlite3
import time
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

ph = PasswordHasher()

# usuarios SQL
# columns = id, nome, idade, senha
usuarios = sqlite3.connect('usuarios.db')
cursor_usuarios = usuarios.cursor()

# produtos SQL
# columns = id, nome, valor, estoque
produtos = sqlite3.connect('produtos.db')
cursor_produtos = produtos.cursor()

# vendas SQL
# columns = id, client_id, produto_id, quantidade, valor_unitario
vendas = sqlite3.connect('vendas.db')
cursor_vendas = vendas.cursor()

# Conectar os outros bancos ao banco de vendas
cursor_vendas.execute("ATTACH DATABASE 'usuarios.db' AS usuarios_db")
cursor_vendas.execute("ATTACH DATABASE 'produtos.db' AS db_produtos")

carrinho = []
sub_total = 0
id_compra = None


# Login
def login():
    global id_compra

    time.sleep(0.2)
    print('iniciando sistema de login')

    nome = input('digite o nome de usuario: ')
    senha = input('digite sua senha: ')

    cursor_usuarios.execute('''
        SELECT senha, id FROM usuarios
        WHERE nome = ?
    ''', (nome,))

    validar = cursor_usuarios.fetchone()

    if validar:
        try:
            senha_hash = validar[0]
            ph.verify(senha_hash, senha)

            print('acesso concedido')
            time.sleep(0.5)

            id_compra = validar[1]
            loja()

        except VerifyMismatchError:
            print('senha incorreta.')
            time.sleep(0.5)

    else:
        print('usuario não encontrado')
        print('deseja realizar um cadastro?')
        print('1- sim // 2- não')

        try:
            of = int(input('digite o valor:'))
        except ValueError:
            print('digite apenas numeros')
            return

        if of == 1:
            cadastro()

        elif of == 2:
            return


# Cadastro
def cadastro():
    time.sleep(0.2)
    nome_cad = input('crie um nome de usuario: ')

    while True:
        try:
            idade = int(input('digite sua idade: '))
            break
        except ValueError:
            print('digite apenas numeros nesse campo!')

    senha_cad = input('digite sua senha de usuario: ')
    senha_hash = ph.hash(senha_cad)

    cursor_usuarios.execute("""
        INSERT INTO usuarios (nome, idade, senha)
        VALUES (?, ?, ?)
    """, (nome_cad, idade, senha_hash))

    usuarios.commit()

    print(
        f'você foi cadastrado com sucesso {nome_cad}, '
        'Bem vindo, faça login e aproveite nosso sistema.'
    )
    time.sleep(2)


# Ver produtos
def ver_produtos():
    global sub_total

    cursor_produtos.execute('''
        SELECT id, nome, valor FROM produtos
    ''')

    resultado = cursor_produtos.fetchall()

    print('======PRODUTOS======')
    print('===nome=====valor===')

    for produto in resultado:
        print(f'{produto[0]}: {produto[1]} - R${produto[2]:.2f}')

    time.sleep(1)

    def recalcular_sub_total():
        global sub_total
        sub_total = 0

        for item in carrinho:
            sub_total += item['total']

        return sub_total

    while True:
        try:
            print('0 - Voltar/remover item do carrinho')
            carrinho_produto = int(
                input('digite o numero do produto que deseja adicionar ao carrinho: ')
            )

            if carrinho_produto == 0:
                print('1- Remover item do carrinho')
                print('2- Voltar')

                opp = int(input('digite sua opção: '))

                if opp == 1:
                    for mostre in carrinho:
                        print(mostre)

                    carrier = int(
                        input('digite o id do produto que deseja remover: ')
                    )

                    for item in carrinho:
                        if carrier == item['id']:
                            carrinho.remove(item)
                            break

                    recalcular_sub_total()

                elif opp == 2:
                    return

                continue

            carrinho_estoque = int(
                input('digite a quantidade desejada do produto: ')
            )

        except ValueError:
            print('Digite apenas numeros')
            continue

        if carrinho_estoque <= 0:
            print('estoque invalido')
            continue

        cursor_produtos.execute('''
            SELECT id, estoque, valor, nome FROM produtos
            WHERE id = ?
        ''', (carrinho_produto,))

        resultado_produtos = cursor_produtos.fetchone()

        if resultado_produtos is None:
            print('produto inexistente')
            continue

        novo_estoque = resultado_produtos[1] - carrinho_estoque

        if novo_estoque < 0:
            print('estoque insuficiente, favor selecione outro produto')
            continue

        valor_conta = carrinho_estoque * resultado_produtos[2]

        sub_total += valor_conta

        item = {
            'id': carrinho_produto,
            'nome': resultado_produtos[3],
            'valor': resultado_produtos[2],
            'quantidade': carrinho_estoque,
            'total': valor_conta
        }

        carrinho.append(item)

        for itens in carrinho:
            print(itens)

        print(f'Subtotal: R$ {sub_total:.2f}')


# Comprar
def comprar():
    global carrinho, sub_total

    print('deseja confirmar a compra?')
    print('1- Sim')
    print('2- Não')

    try:
        confirmar = int(input('digite o valor: '))
    except ValueError:
        print('digite apenas numeros!')
        return

    if confirmar == 1:
        if not carrinho:
            print('seu carrinho está vazio.')
            return

        print('iniciando sua compra...')

        for compras in carrinho:
            cursor_vendas.execute('''
                INSERT INTO vendas
                    (client_id, produto_id, quantidade, valor_unitario)
                VALUES (?, ?, ?, ?)
            ''', (
                id_compra,
                compras['id'],
                compras['quantidade'],
                compras['valor']
            ))

        vendas.commit()

        print('compra registrada com sucesso!')
        carrinho = []
        sub_total = 0

    elif confirmar == 2:
        carrinho = []
        sub_total = 0
        print('compra cancelada.')


# Ver carrinho
def ver_carrinho():
    for mostrar in carrinho:
        print(mostrar)

    print(f'Subtotal: R$ {sub_total:.2f}')


# Histórico de compras
def visualizar_compras():
    cursor_vendas.execute('''
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
    ''', (id_compra,))

    compras = cursor_vendas.fetchall()

    if not compras:
        print('Nenhuma compra encontrada.')
        return

    print('\\n===== HISTÓRICO DE COMPRAS =====')

    for mostrar in compras:
        print(f'''
ID do cliente: {mostrar[0]}
Nome do cliente: {mostrar[1]}
Produto: {mostrar[2]}
Quantidade: {mostrar[3]}
Valor unitário: R$ {mostrar[4]:.2f}
----------------------------
''')


# Sair
def sair():
    return


# Loja
def loja():
    while True:
        print('\\n===== MERCADO BANANA =====')
        print('1 - Ver produtos')
        print('2 - Comprar')
        print('3 - Ver carrinho')
        print('4 - Visualizar compras')
        print('5 - Sair')

        try:
            option_menu = int(input('digite a opção desejada: '))
        except ValueError:
            print('digite apenas numeros!!!')
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
            print('opção inválida')


# Parte principal
while True:
    print('==============================')
    print('         MERCADINHO')
    print('    Sistema de Login')
    print('==============================')
    print()
    print('[1] Login')
    print('[2] Cadastro')
    print('[3] Sair')

    try:
        opcao = int(input('Escolha uma opção: '))
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
        print('opção inválida')

usuarios.close()
produtos.close()
vendas.close()
