from flask import (
    Flask, render_template, request,flash,
    redirect, url_for, session, jsonify
)
import bcrypt
from models.receita import Receita, Preparos, Ingrediente
from models.usuario import Usuario
from models.cardapio import Cardapio, Refeicoes_Cardapio
from dao.receita_dao import ReceitaDAO
from dao.usuario_dao import UsuarioDAO
from dao.cardapio_dao import CardapioDAO

print("Iniciando o aplicativo Flask...")
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'
usuario_dao = UsuarioDAO()
receita_dao = ReceitaDAO()
cardapio_dao = CardapioDAO()
dao_receita = ReceitaDAO()  # precisa ter método para listar receitas do usuário

#=======================================ROTAS CADASTRO========================================
@app.route('/cadastrar_usuario', methods=['GET', 'POST'])
def cadastrar_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        # Verifica se o email já existe
        if usuario_dao.email_existe(email):
            flash('Email já está cadastrado.📩')
            return render_template('cadastro.html')
        try:
            # Gera hash da senha
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            # Cria instância do modelo Usuario
            novo_usuario = Usuario(
                nome=nome,
                email=email,
                senha=senha_hash
            )
            # Insere no banco
            usuario_dao.inserir(novo_usuario)
            flash(' Usuario cadastrado com sucesso! 🧑‍🍳👩‍🍳')
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Erro ao cadastrar: {e}")
            flash('Ocorreu um erro ao cadastrar o paciente. Tente novamente.❌')
            return render_template('cadastro.html')

    return render_template('cadastro.html')


#=======================================ROTAS LOGIN===========================================
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        # Busca o usuário pelo email
        usuario = UsuarioDAO().buscar_por_email_login(email)
        print(usuario)
        if usuario:
            # A senha armazenada no banco está codificada (hash), então comparamos com a senha inserida
            senha_armazenada = usuario.senha.encode('utf-8')  # A senha armazenada no banco está em bytes
            # Verifica se a senha inserida corresponde ao hash armazenado
            print('oi')
            if bcrypt.checkpw(senha.encode('utf-8'), senha_armazenada):
                # Se as credenciais estiverem corretas, armazena o usuário na sessão
                session['usuario_id'] = usuario.id
                session['usuario_nome'] = usuario.nome
                session['email_usuario'] = usuario.email
                return redirect(url_for('minhas_receitas', id_usuario=usuario.id, nome_usuario=usuario.nome,email_email=usuario.email))
        # Caso não encontre o usuário ou a senha não corresponda
        flash('Login inválido. Verifique suas credenciais ❌.')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        if usuario_dao.buscar_por_email(email):
            return "Email já cadastrado", 400
        novo_usuario = Usuario(None, nome, email, senha)
        usuario_dao.inserir(novo_usuario)
        return redirect(url_for('login'))
    return render_template('cadastro.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))




#=======================================ROTAS MINHAS RECEITAS===========================================

@app.route('/minhas_receitas')
def minhas_receitas():
    id_usuario = session['usuario_id']  
    nome_usuario = session['usuario_nome']
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('minhas_receitas.html', nome_usuario=nome_usuario, id_usuario=id_usuario)



@app.route('/api/receitas', methods=['POST'])
def api_adicionar_receita():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    dados = request.json
    usuario_id = session['usuario_id']
    receita = Receita(None, dados['titulo'], dados['porcoes'], dados['tempoPreparo'], dados['tipo'], None)
    ingredientes = [
        Ingrediente(None, i['produto'], float(i['quantidade']), i['unidade'], None)
        for i in dados['ingredientes']
    ]
    preparos = [
        Preparos(None, idx + 1, passo, None)
        for idx, passo in enumerate(dados['modoPreparo'])
    ]
    receita_dao.inserir(receita, ingredientes, preparos, usuario_id)
    return jsonify({'mensagem': 'Receita adicionada com sucesso'})


@app.route('/api/receitas/<int:receita_id>', methods=['DELETE'])
def api_excluir_receita(receita_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401

    receita_dao.excluir(receita_id)
    return jsonify({'mensagem': 'Receita excluída com sucesso'})

#=======================================ROTAS PRECIFICAR===========================================

@app.route('/precificar')
def precificacao():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('precificar.html', nome_usuario=session['usuario_nome'])

@app.route('/atualizar_preco', methods=['POST'])
def atualizar_preco():
    data = request.json
    receita_id = data['receita_id']
    preco_total = data['preco_total']

    receita_dao.atualizar_preco(preco_total, receita_id)
    return jsonify({'status': 'sucesso', 'preco': preco_total})



##=======================================ROTAS CARDAPIO===========================================
@app.route('/cardapio')
def cardapio():
    id_usuario = session['usuario_id']  
    nome_usuario = session['usuario_nome']
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('cardapio.html', nome_usuario=nome_usuario, id_usuario=id_usuario)

@app.route('/cardapio/adicionar', methods=['POST'])
def adicionar_receita_cardapio():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    dados = request.json
    usuario_id = session['usuario_id']
    dia_semana = dados.get('dia')  # Corrigido
    tipo = dados.get('refeicao')     # Corrigido
    receita_id = dados.get('receita_id')  # Corrigido
    cardapio_dao.adicionar_ao_cardapio({
        'dia': dia_semana,
        'refeicao': tipo,
        'receita_id': receita_id,
        'usuario_id': usuario_id
    })
    return jsonify({'sucesso': True}), 200

@app.route('/api/cardapio/excluir', methods=['POST'])
def excluir_receita_cardapio():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401
    dados = request.get_json()
    usuario_id = session['usuario_id']
    dia_semana = dados.get('dia')
    tipo = dados.get('refeicao')
    receita_id = dados.get('receita_id', {}).get('id')
    print(usuario_id)
    print(dia_semana)
    print(tipo)
    print(receita_id)
    if not all([dia_semana, tipo, receita_id]):
        return jsonify({'erro': 'Dados incompletos'}), 400
    try:
        cardapio_dao.remover_do_cardapio({
            'dia': dia_semana,
            'refeicao': tipo,
            'receita_id': receita_id,
            'usuario_id': usuario_id
        })
        print("certo")
        return jsonify({'sucesso': True}), 200
    except Exception as e:
        print("nÃAAAAAAAAAAOOOOO")
        return jsonify({'erro': str(e)}), 500
    


@app.route('/api/cardapio', methods=['GET'])
def visualizar_cardapio():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Usuário não autenticado'}), 401

    usuario_id = session['usuario_id']
    cardapio = cardapio_dao.visualizar_receitas_cardapio(usuario_id)
    return jsonify(cardapio), 200





#=======================================ROTAS MEU PERFIL===========================================

@app.route('/meu_perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    # Obtendo o id do usuário da sessão
    usuario_id = session.get('usuario_id')
    return render_template(
        'meu_perfil.html',
        nome_usuario=session.get('usuario_nome'),
        email_usuario=session.get('email_usuario'),
        receitas_criadas=usuario_dao.contar_receitas_do_usuario(usuario_id),
        id_usuario=usuario_id  # Passando o id do usuário para o template
    )

@app.route('/atualizar_usuario', methods=['POST'])
def atualizar_usuario():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    data = request.json
    usuario_id = session['usuario_id']
    nome = data.get('nome')
    email = data.get('email')
    dao = UsuarioDAO()
    dao.atualizar(usuario_id, nome, email)
    session['usuario_nome'] = nome
    session['email_usuario'] = email
    return jsonify({'status': 'sucesso'})



@app.route('/excluir_conta', methods=['POST'])
def excluir_conta():
    data = request.json
    usuario_id = data.get('usuario_id')
    print(f"Excluindo conta com ID: {usuario_id}")  # Verifique se o ID é impresso corretamente
    # Verifique se o usuario_dao.excluir(usuario_id) está funcionando corretamente
    usuario_dao.excluir(usuario_id)
    
    return jsonify({'status': 'conta excluída'})






#===================================API´S (BUSCAR INFOS NO BD)==========================================
@app.route('/api/receitas', methods=['GET'])
def api_listar_receitas():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401

    usuario_id = session['usuario_id']
    receitas = receita_dao.listar_por_usuario(usuario_id)

    receitas_json = []
    for r in receitas:
        receita = r['receita']
        ingredientes = r['ingredientes']
        preparos = r['preparos']

        receitas_json.append({
            'id': receita.id,
            'titulo': receita.nome,
            'tipo': receita.tipo,
            'preco': receita.preco,
            'tempoPreparo': receita.tempo_preparo,  
            'porcoes': receita.porcao,              
            'ingredientes': [{
                'produto': ing.nome,
                'quantidade': ing.quantidade,
                'unidade': ing.unidade
            } for ing in ingredientes],
            'modoPreparo': [prep.descricao for prep in sorted(preparos, key=lambda p: p.etapa)]
        })
            
    return jsonify(receitas_json)


@app.route('/api/usuario/<int:usuario_id>', methods=['GET'])
def buscar_usuario_por_id(usuario_id):
    usuario = usuario_dao.buscar_por_id(usuario_id)
    if usuario:
        return jsonify({
            'id': usuario.id,
            'nome': usuario.nome,
            'email': usuario.email,
            'foto': usuario.foto
        })
    else:
        return jsonify({'erro': 'Usuário não encontrado'}), 404




if __name__ == '__main__':
    app.run(debug=True)
