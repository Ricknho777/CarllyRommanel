# app.py - CONFIGURADO PARA PRODUÇÃO COM VARIÁVEIS DE AMBIENTE
from flask import Flask, render_template, jsonify, request, session, redirect
from flask_cors import CORS  # ADICIONADO CORS
from apimercadopago import criar_preferencia_pagamento, testar_conexao_direta, verificar_ambiente_mercado_pago
from produtos import Produto, GerenciadorProdutos
from produtos_data import criar_produtos_iniciais
import json
import os
import time
import hashlib
import sqlite3  # ADICIONADO PARA BANCO DE DADOS
from datetime import datetime
from dotenv import load_dotenv
import secrets

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

app = Flask(__name__)

# ========== CONFIGURAÇÃO CORS ==========
# ADICIONADO: Permitir CORS para resolver erros de conexão
CORS(app, resources={
    r"/*": {
        "origins": "*",  # Permite todas as origens (ajuste conforme necessário)
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# ========== CONFIGURAÇÃO PARA HTTP/HTTPS NO RENDER ==========

# Configurações específicas para Render
FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'True').lower() == 'true'
ALLOW_HTTP = os.environ.get('ALLOW_HTTP', 'False').lower() == 'true'
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL', '')

# Configurar esquema preferido baseado na URL externa
if RENDER_EXTERNAL_URL:
    if RENDER_EXTERNAL_URL.startswith('https://'):
        PREFERRED_URL_SCHEME = 'https'
    elif RENDER_EXTERNAL_URL.startswith('http://'):
        PREFERRED_URL_SCHEME = 'http'
    else:
        PREFERRED_URL_SCHEME = 'https'  # Padrão para segurança
else:
    PREFERRED_URL_SCHEME = 'https'

# Configurar o Flask para usar o esquema correto
app.config['PREFERRED_URL_SCHEME'] = PREFERRED_URL_SCHEME
app.config['APPLICATION_ROOT'] = os.environ.get('APPLICATION_ROOT', '/')

# ========== CONFIGURAÇÕES DE VARIÁVEIS DE AMBIENTE ==========

# Chave secreta para sessões do Flask
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configurações de ambiente
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
FLASK_DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# PORT - Deixe o Render gerenciar automaticamente
PORT = int(os.environ.get('PORT', 5000))

# EMAIL E SENHA DO ADMIN - DO .env
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@romaneljoias.com')
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH', '')

# Verificação de segurança
if not ADMIN_PASSWORD_HASH:
    print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] AVISO: ADMIN_PASSWORD_HASH não configurado!")
    print(f"   Configure no .env: ADMIN_PASSWORD_HASH=hash_gerado_com_sha256")
    print(f"   Gerar hash: python -c \"import hashlib; print(hashlib.sha256('senha'.encode()).hexdigest())\"")
    print(f"   Painel admin estará INACESSÍVEL até configurar!")
    # Define um hash inválido para bloquear acesso
    ADMIN_PASSWORD_HASH = "CONFIGURE_ADMIN_PASSWORD_HASH_IN_ENV"

# Token de API para autenticação (para produção)
ADMIN_API_TOKEN = os.environ.get('ADMIN_API_TOKEN', '')

# Caminhos dos arquivos JSON
PRODUTOS_BACKUP_FILE = os.environ.get('PRODUTOS_BACKUP_FILE', 'produtos_backup.json')
PRODUTOS_TEMP_FILE = os.environ.get('PRODUTOS_TEMP_FILE', 'produtos_temp.json')

# Configurações de sessão
app.config['PERMANENT_SESSION_LIFETIME'] = int(os.environ.get('PERMANENT_SESSION_LIFETIME', 3600))

# Configurar cookies seguros baseado no esquema
if PREFERRED_URL_SCHEME == 'https':
    app.config['SESSION_COOKIE_SECURE'] = True
else:
    app.config['SESSION_COOKIE_SECURE'] = False

app.config['SESSION_COOKIE_HTTPONLY'] = os.environ.get('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')

# Configurações de frete
DEFAULT_FRETE = float(os.environ.get('DEFAULT_FRETE', 5.00))
FRETE_GRATIS_ACIMA = float(os.environ.get('FRETE_GRATIS_ACIMA', 150.00))

# ========== BANCO DE DADOS ==========
DATABASE = 'database.db'

def init_db():
    """Inicializa o banco de dados SQLite"""
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Tabela de tokens de admin
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de usuários/clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                items TEXT,
                total REAL,
                status TEXT DEFAULT 'pendente',
                payment_id TEXT,
                external_reference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Banco de dados inicializado!")
        
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro ao inicializar banco de dados: {str(e)}")

# Inicializar banco de dados
init_db()

# ========== FUNÇÕES AUXILIARES BANCO DE DADOS ==========

def get_db_connection():
    """Obtém conexão com o banco de dados"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_user(name, email, password, phone=None, address=None):
    """Cria um novo usuário no banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se email já existe
        cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return {"success": False, "error": "Este e-mail já está cadastrado!"}
        
        # Inserir novo usuário (em produção, usar hash de senha!)
        cursor.execute('''
            INSERT INTO users (name, email, password, phone, address)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, email, password, phone, address))
        
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        
        return {"success": True, "user_id": user_id, "message": "Usuário criado com sucesso!"}
        
    except Exception as e:
        return {"success": False, "error": f"Erro ao criar usuário: {str(e)}"}

def authenticate_user(email, password):
    """Autentica um usuário"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return {"success": True, "user": dict(user)}
        else:
            return {"success": False, "error": "E-mail ou senha incorretos!"}
            
    except Exception as e:
        return {"success": False, "error": f"Erro ao autenticar: {str(e)}"}

# ========== FUNÇÕES DE GERENCIAMENTO DE TOKENS ADMIN ==========

def save_admin_token(token, email, expires_in_hours=24):
    """Salva um token de admin no banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        expires_at = datetime.now().timestamp() + (expires_in_hours * 3600)
        
        # Inserir novo token
        cursor.execute('''
            INSERT INTO admin_tokens (token, email, expires_at)
            VALUES (?, ?, ?)
        ''', (token, email, expires_at))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao salvar token: {str(e)}")
        return False

def verify_admin_token(token):
    """Verifica se um token de admin é válido"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM admin_tokens 
            WHERE token = ? AND expires_at > ?
        ''', (token, datetime.now().timestamp()))
        
        token_data = cursor.fetchone()
        conn.close()
        
        if token_data:
            # Token válido
            return {"valid": True, "email": token_data['email']}
        else:
            # Token inválido ou expirado
            return {"valid": False, "error": "Token inválido ou expirado"}
            
    except Exception as e:
        print(f"❌ Erro ao verificar token: {str(e)}")
        return {"valid": False, "error": str(e)}

def delete_admin_token(token):
    """Remove um token de admin"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM admin_tokens WHERE token = ?', (token,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Erro ao deletar token: {str(e)}")
        return False

def cleanup_expired_tokens():
    """Limpa tokens expirados do banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM admin_tokens WHERE expires_at <= ?', (datetime.now().timestamp(),))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            print(f"🧹 [{datetime.now().strftime('%H:%M:%S')}] Limpos {deleted_count} tokens expirados")
            
    except Exception as e:
        print(f"❌ Erro ao limpar tokens expirados: {str(e)}")

# ========== INICIALIZAÇÃO DO SISTEMA ==========

# Inicializar gerenciador de produtos
gerenciador = GerenciadorProdutos()

# Carregar produtos iniciais
for produto in criar_produtos_iniciais():
    gerenciador.adicionar_produto(produto)

def verificar_admin_senha(senha_fornecida):
    """Verifica se a senha do admin está correta (aceita texto ou hash)"""
    if not senha_fornecida or not ADMIN_PASSWORD_HASH:
        print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Tentativa de login sem senha ou hash não configurado")
        return False
    
    # Se o hash estiver configurado como placeholder, bloqueia
    if ADMIN_PASSWORD_HASH == "CONFIGURE_ADMIN_PASSWORD_HASH_IN_ENV":
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Acesso negado: ADMIN_PASSWORD_HASH não configurado no .env")
        return False
    
    # Se a senha fornecida tem 64 caracteres (hash SHA256), assume que é um hash
    if len(senha_fornecida) == 64 and all(c in '0123456789abcdefABCDEF' for c in senha_fornecida):
        # O frontend enviou um hash SHA256
        print(f"🔐 [{datetime.now().strftime('%H:%M:%S')}] Recebido hash SHA256 do frontend")
        return senha_fornecida.lower() == ADMIN_PASSWORD_HASH.lower()
    else:
        # O frontend enviou senha em texto
        print(f"🔐 [{datetime.now().strftime('%H:%M:%S')}] Recebido senha em texto do frontend")
        hash_senha = hashlib.sha256(senha_fornecida.encode()).hexdigest()
        return hash_senha.lower() == ADMIN_PASSWORD_HASH.lower()

def verificar_token_api(token):
    """Verifica se o token de API é válido"""
    if not token:
        return False
    
    # Primeiro verifica se é um token de admin do banco de dados
    token_result = verify_admin_token(token)
    if token_result["valid"]:
        return True
    
    # Se ADMIN_API_TOKEN estiver configurado, verifica
    if ADMIN_API_TOKEN:
        return token == ADMIN_API_TOKEN
    
    # Se não houver token configurado, verifica se é uma senha válida
    return verificar_admin_senha(token)

def verificar_autenticacao_admin():
    """Verifica se a requisição está autenticada para operações admin"""
    # Em produção, todas as operações admin requerem autenticação
    if FLASK_ENV == 'production' and not FLASK_DEBUG:
        # Verificar cabeçalho de autorização
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Autenticação falhou: Cabeçalho Authorization ausente ou mal formatado")
            return False
        
        # Extrair e verificar o token
        token = auth_header.replace('Bearer ', '').strip()
        
        if not token:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Autenticação falhou: Token vazio")
            return False
        
        # Verificar token
        if verificar_token_api(token):
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Autenticação bem-sucedida via token API")
            return True
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Autenticação falhou: Token/senha inválido")
            return False
    
    # Em desenvolvimento ou debug, pode permitir sem autenticação
    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Modo desenvolvimento: Autenticação simplificada")
    return True

def salvar_produtos_json():
    """Salva os produtos em um arquivo JSON"""
    try:
        produtos_json = gerenciador.to_json()
        with open(PRODUTOS_BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(produtos_json, f, ensure_ascii=False, indent=2)
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Produtos salvos em {PRODUTOS_BACKUP_FILE} ({len(produtos_json)} produtos)")
        return True
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro ao salvar produtos: {str(e)}")
        return False

def carregar_produtos_backup():
    """Carrega produtos do arquivo de backup se existir"""
    try:
        with open(PRODUTOS_BACKUP_FILE, 'r', encoding='utf-8') as f:
            produtos_data = json.load(f)
        
        print(f"📦 [{datetime.now().strftime('%H:%M:%S')}] Carregando {len(produtos_data)} produtos do backup...")
        
        # Limpar produtos atuais
        gerenciador.produtos.clear()
        
        # Adicionar produtos do backup
        for produto_data in produtos_data:
            try:
                produto = Produto.from_dict(produto_data)
                gerenciador.adicionar_produto(produto)
            except Exception as e:
                print(f"⚠️ Erro ao carregar produto {produto_data.get('id')}: {str(e)}")
        
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Carregados {len(gerenciador.produtos)} produtos do backup")
        return True
    except FileNotFoundError:
        print(f"ℹ️ [{datetime.now().strftime('%H:%M:%S')}] Nenhum backup encontrado, usando produtos iniciais")
        return False
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro ao carregar backup: {str(e)}")
        return False

# Carregar produtos do backup (se existir) ao iniciar
print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Inicializando sistema...")
print(f"🔧 Ambiente: {FLASK_ENV}")
print(f"🐛 Debug: {FLASK_DEBUG}")
print(f"📧 Admin email: {ADMIN_EMAIL}")
print(f"🔐 Admin hash configurado: {'✅ Sim' if ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_HASH != 'CONFIGURE_ADMIN_PASSWORD_HASH_IN_ENV' else '❌ Não (configure no .env)'}")
print(f"🔑 Token API configurado: {'✅ Sim' if ADMIN_API_TOKEN else '⚠️ Não (usando senha como fallback)'}")

# Verificar configuração Render
if RENDER_EXTERNAL_URL:
    print(f"🌐 Render URL configurada: {RENDER_EXTERNAL_URL}")
    print(f"🔒 Esquema preferido: {PREFERRED_URL_SCHEME}")
    print(f"🔄 Forçar HTTPS: {'✅ Sim' if FORCE_HTTPS else '❌ Não'}")
    print(f"🔓 Permitir HTTP: {'✅ Sim' if ALLOW_HTTP else '❌ Não'}")

carregar_produtos_backup()

# Verificar se há produtos iniciais
if len(gerenciador.produtos) == 0:
    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Nenhum produto carregado. Adicionando produtos iniciais...")
    for produto in criar_produtos_iniciais():
        gerenciador.adicionar_produto(produto)
    salvar_produtos_json()

print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Sistema inicializado com {len(gerenciador.produtos)} produtos")

# Limpar tokens expirados ao iniciar
cleanup_expired_tokens()

# ========== MIDDLEWARE PARA TRATAR HTTP/HTTPS NO RENDER ==========

@app.before_request
def before_request():
    """Middleware para lidar com HTTP/HTTPS no Render"""
    
    # Verificar se estamos no Render
    is_render = os.environ.get('RENDER', False)
    
    if is_render and RENDER_EXTERNAL_URL:
        # Se forçar HTTPS e a requisição for HTTP
        if FORCE_HTTPS and request.headers.get('X-Forwarded-Proto') == 'http':
            # Redirecionar para HTTPS
            https_url = request.url.replace('http://', 'https://', 1)
            return redirect(https_url, code=301)
    
    # Limpar tokens expirados a cada 10 minutos
    if request.endpoint and 'admin' in request.endpoint:
        current_time = datetime.now().timestamp()
        if current_time % 600 < 1:  # Aproximadamente a cada 10 minutos
            cleanup_expired_tokens()
    
    # Continuar com a requisição normalmente
    return None

# ========== ROTAS PRINCIPAIS ==========

@app.route('/')
def index():
    """Página principal"""
    print(f"🌐 [{datetime.now().strftime('%H:%M:%S')}] Página principal acessada")
    return render_template('index.html')

@app.route('/checkout.html')
def checkout_page():
    """Página de checkout"""
    print(f"💰 [{datetime.now().strftime('%H:%M:%S')}] Página de checkout acessada")
    return render_template('checkout.html')

# ========== ROTA DE REDIRECIONAMENTO ADMIN ==========

@app.route('/admin/redirect')
def admin_redirect():
    """Rota de redirecionamento para admin após login"""
    print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Redirecionamento para admin")
    
    # Verificar se há token na URL ou sessão
    token = request.args.get('token')
    
    if token:
        # Verificar se o token é válido
        token_result = verify_admin_token(token)
        if token_result["valid"]:
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Token válido, redirecionando para admin")
            return redirect('/admin')
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Token inválido, redirecionando para login")
            return redirect('/?login=admin')
    else:
        # Se não houver token, verificar se está na sessão
        if 'user_id' in session:
            # Verificar se é admin
            user_email = session.get('user_email')
            if user_email == ADMIN_EMAIL:
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Admin na sessão, redirecionando")
                return redirect('/admin')
    
    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Nenhuma autenticação encontrada, redirecionando para login")
    return redirect('/?login=admin')

# ========== ROTAS DE AUTENTICAÇÃO E USUÁRIO ==========

@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register_user():
    """Cadastra um novo usuário"""
    if request.method == 'OPTIONS':
        return '', 200  # Responde preflight CORS
    
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                "success": False,
                "error": "Nenhum dado recebido"
            }), 400
        
        nome = dados.get('nome', '').strip()
        email = dados.get('email', '').strip()
        senha = dados.get('senha', '').strip()
        confirmar_senha = dados.get('confirmar_senha', '').strip()
        telefone = dados.get('telefone', '').strip()
        endereco = dados.get('endereco', '').strip()
        
        # Validações
        if not nome:
            return jsonify({"success": False, "error": "Nome é obrigatório"}), 400
        
        if not email or '@' not in email:
            return jsonify({"success": False, "error": "E-mail válido é obrigatório"}), 400
        
        if not senha:
            return jsonify({"success": False, "error": "Senha é obrigatória"}), 400
        
        if senha != confirmar_senha:
            return jsonify({"success": False, "error": "As senhas não coincidem"}), 400
        
        # Criar usuário (EM PRODUÇÃO, USE HASH DE SENHA!)
        resultado = create_user(nome, email, senha, telefone, endereco)
        
        if resultado["success"]:
            return jsonify({
                "success": True,
                "message": "Cadastro realizado com sucesso!",
                "user_id": resultado["user_id"]
            })
        else:
            return jsonify({
                "success": False,
                "error": resultado["error"]
            }), 400
            
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro no cadastro: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Erro interno no servidor"
        }), 500

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def login_user():
    """Autentica um usuário OU admin - ROTA UNIFICADA"""
    if request.method == 'OPTIONS':
        return '', 200  # Responde preflight CORS
    
    try:
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                "success": False,
                "error": "Nenhum dado recebido"
            }), 400
        
        # Compatibilidade com diferentes formatos de campos
        email = dados.get('email', dados.get('username', '')).strip()
        senha = dados.get('senha', dados.get('password', ''))
        
        print(f"🔐 [{datetime.now().strftime('%H:%M:%S')}] Tentativa de login recebida")
        print(f"   Email: {email}")
        print(f"   Senha fornecida (tamanho): {len(senha) if senha else 0}")
        
        # Validações básicas
        if not email or not senha:
            return jsonify({"success": False, "error": "E-mail e senha são obrigatórios"}), 400
        
        # VERIFICAÇÃO ESPECIAL PARA ADMIN
        if email == ADMIN_EMAIL:
            print(f"🔐 [{datetime.now().strftime('%H:%M:%S')}] Login de admin detectado")
            
            # Verificar senha do admin
            if verificar_admin_senha(senha):
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Login admin bem-sucedido para {email}")
                
                # Gerar token seguro
                token = secrets.token_urlsafe(64)
                
                # Salvar token no banco de dados
                expires_in_hours = 24
                save_admin_token(token, email, expires_in_hours)
                
                return jsonify({
                    "success": True,
                    "message": "Login administrativo realizado com sucesso",
                    "token": token,
                    "user": {
                        "name": "Administrador",
                        "email": email,
                        "role": "admin"
                    },
                    "redirect_url": f"/admin/redirect?token={token}",  # URL DE REDIRECIONAMENTO DIRETO
                    "expires_in": expires_in_hours * 3600,
                    "environment": FLASK_ENV,
                    "requires_auth": True
                })
            else:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Senha incorreta para admin")
                return jsonify({
                    "success": False,
                    "error": "Senha incorreta"
                }), 401
        
        # SE NÃO FOR ADMIN, FAZ LOGIN DE USUÁRIO COMUM
        print(f"👤 [{datetime.now().strftime('%H:%M:%S')}] Tentando login de usuário comum: {email}")
        
        # Autenticar usuário (EM PRODUÇÃO, USE HASH DE SENHA!)
        resultado = authenticate_user(email, senha)
        
        if resultado["success"]:
            # Armazenar na sessão (em produção, use JWT!)
            session['user_id'] = resultado["user"]["id"]
            session['user_name'] = resultado["user"]["name"]
            session['user_email'] = resultado["user"]["email"]
            
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Login usuário bem-sucedido para {email}")
            
            return jsonify({
                "success": True,
                "message": "Login realizado com sucesso!",
                "user": {
                    "id": resultado["user"]["id"],
                    "name": resultado["user"]["name"],
                    "email": resultado["user"]["email"],
                    "role": "user"
                },
                "redirect_url": "/"  # Redireciona para a página principal
            })
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Login usuário falhou: {resultado.get('error')}")
            return jsonify({
                "success": False,
                "error": resultado.get("error", "E-mail ou senha incorretos")
            }), 401
            
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro no login: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Erro interno no servidor: {str(e)}"
        }), 500

@app.route('/api/logout', methods=['POST'])
def logout_user():
    """Desconecta o usuário"""
    session.clear()
    return jsonify({"success": True, "message": "Logout realizado com sucesso!"})

@app.route('/api/user/check', methods=['GET'])
def check_user_session():
    """Verifica se o usuário está logado"""
    if 'user_id' in session:
        return jsonify({
            "success": True,
            "is_logged_in": True,
            "user": {
                "id": session.get('user_id'),
                "name": session.get('user_name'),
                "email": session.get('user_email')
            }
        })
    else:
        return jsonify({
            "success": True,
            "is_logged_in": False
        })

# ========== API DE PRODUTOS (PÚBLICA) ==========

@app.route('/api/produtos')
def get_produtos():
    """API: Retorna todos os produtos"""
    try:
        produtos_json = gerenciador.to_json()
        print(f"🛍️ [{datetime.now().strftime('%H:%M:%S')}] API produtos: retornando {len(produtos_json)} produtos")
        return jsonify(produtos_json)
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro na API produtos: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ========== CHECKOUT E PAGAMENTO ==========

@app.route('/checkout', methods=['POST', 'OPTIONS'])
def checkout():
    """Processa o checkout e cria pagamento no Mercado Pago"""
    if request.method == 'OPTIONS':
        return '', 200  # Responde preflight CORS
    
    try:
        print(f"=== [{datetime.now().strftime('%H:%M:%S')}] INICIANDO PROCESSAMENTO DE CHECKOUT ===")
        
        dados = request.get_json()
        
        if not dados:
            return jsonify({
                "success": False,
                "error": "Nenhum dado recebido"
            }), 400
        
        # Obter produtos do carrinho
        carrinho = dados.get('carrinho', [])
        if not carrinho:
            return jsonify({
                "success": False,
                "error": "Carrinho vazio"
            }), 400
        
        # VALOR DO FRETE - Usar variável de ambiente
        frete_valor = float(dados.get('frete', DEFAULT_FRETE))
        
        # Aplicar frete grátis se configurado
        if FRETE_GRATIS_ACIMA > 0:
            total_produtos = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in carrinho)
            if total_produtos >= FRETE_GRATIS_ACIMA:
                frete_valor = 0.00
                print(f"🚚 [{datetime.now().strftime('%H:%M:%S')}] Frete grátis aplicado (compra acima de R$ {FRETE_GRATIS_ACIMA:.2f})")
        
        # Calcular total dos produtos
        total_produtos = 0
        for item in carrinho:
            item_price = float(item.get('price', 0))
            item_quantity = int(item.get('quantity', 1))
            total_produtos += item_price * item_quantity
        
        total_com_frete = total_produtos + frete_valor
        
        # Validar dados do cliente
        nome = dados.get('nome', '').strip()
        email = dados.get('email', '').strip()
        
        if not nome:
            return jsonify({
                "success": False,
                "error": "Nome é obrigatório"
            }), 400
        
        if not email or '@' not in email:
            return jsonify({
                "success": False,
                "error": "Email válido é obrigatório"
            }), 400
        
        dados_cliente = { 
            "nome": nome,
            "email": email
        }

        # Criar preferência no Mercado Pago COM FRETE
        resultado = criar_preferencia_pagamento(dados_cliente, carrinho, frete_valor, request.url_root)
        
        if resultado.get('sucesso'):
            # Salvar pedido no banco de dados (se usuário logado)
            user_id = session.get('user_id') if 'user_id' in session else None
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO orders (user_id, items, total, status, payment_id, external_reference)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    json.dumps(carrinho),
                    total_com_frete,
                    'pendente',
                    resultado.get('id_preferencia'),
                    resultado.get('external_reference')
                ))
                
                conn.commit()
                order_id = cursor.lastrowid
                conn.close()
                
                print(f"📦 [{datetime.now().strftime('%H:%M:%S')}] Pedido salvo no banco (ID: {order_id})")
                
            except Exception as db_error:
                print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Erro ao salvar pedido no banco: {str(db_error)}")
            
            return jsonify({
                "success": True,
                "message": "Pagamento criado com sucesso!",
                "redirect_url": resultado['url_pagamento'],
                "id_preferencia": resultado.get('id_preferencia'),
                "external_reference": resultado.get('external_reference'),
                "frete_valor": frete_valor,
                "total_produtos": total_produtos,
                "total_com_frete": total_com_frete,
                "frete_gratis": frete_valor == 0 and FRETE_GRATIS_ACIMA > 0,
                "detalhes": {
                    "produtos": total_produtos,
                    "frete": frete_valor,
                    "total": total_com_frete,
                    "frete_gratis_minimo": FRETE_GRATIS_ACIMA if FRETE_GRATIS_ACIMA > 0 else None
                }
            })
        else:
            error_msg = resultado.get('error', 'Erro desconhecido no Mercado Pago')
            return jsonify({
                "success": False,
                "error": f"Erro ao processar pagamento: {error_msg}"
            }), 500
    
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO CHECKOUT: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "error": f"Erro interno no servidor: {str(e)}"
        }), 500

# ========== ROTAS DE CALLBACK DO MERCADO PAGO ==========

@app.route('/callback/success')
def callback_success():
    """Callback para pagamento aprovado"""
    print(f"=== [{datetime.now().strftime('%H:%M:%S')}] CALLBACK SUCCESS CHAMADO ===")
    
    # Parâmetros retornados pelo Mercado Pago
    payment_id = request.args.get('payment_id')
    status = request.args.get('status')
    external_reference = request.args.get('external_reference')
    merchant_order_id = request.args.get('merchant_order_id')
    collection_id = request.args.get('collection_id')
    collection_status = request.args.get('collection_status')
    
    # Se não houver payment_id mas houver collection_id, use collection_id
    if not payment_id and collection_id:
        payment_id = collection_id
    
    # Se não houver parâmetros, pode ser acesso direto à página
    if not payment_id and not external_reference:
        print(f"Acesso direto à página de sucesso (sem parâmetros)")
        return render_template('pagamentoaprovado.html',
                              payment_id="Não disponível",
                              status="approved",
                              mensagem="Pagamento processado com sucesso!",
                              redirect_url="/",
                              redirect_time=60)
    
    # Se chegou sem payment_id mas estamos no callback, tenta buscar da sessão
    if not payment_id:
        # Tenta usar o external_reference como referência
        payment_id = external_reference or f"REF_{int(time.time())}"
    
    # Redirecionar para página de sucesso com os dados
    return render_template('pagamentoaprovado.html', 
                          payment_id=payment_id,
                          status=status or "approved",
                          external_reference=external_reference,
                          mensagem="Pagamento aprovado com sucesso!",
                          redirect_url="/",
                          redirect_time=60)

@app.route('/callback/failure')
def callback_failure():
    """Callback para pagamento recusado"""
    print(f"=== [{datetime.now().strftime('%H:%M:%S')}] CALLBACK FAILURE CHAMADO ===")
    
    # Parâmetros retornados pelo Mercado Pago
    payment_id = request.args.get('payment_id')
    status = request.args.get('status')
    external_reference = request.args.get('external_reference')
    collection_id = request.args.get('collection_id')
    collection_status = request.args.get('collection_status')
    
    # Se não houver payment_id mas houver collection_id, use collection_id
    if not payment_id and collection_id:
        payment_id = collection_id
    
    # Se não houver payment_id, cria um para referência
    if not payment_id:
        payment_id = external_reference or f"REF_{int(time.time())}"
    
    return render_template('pagamentorecusado.html',
                          status=status or "rejected",
                          payment_id=payment_id,
                          external_reference=external_reference,
                          mensagem="Pagamento recusado. Tente novamente ou use outro método de pagamento.",
                          redirect_url="/checkout.html",
                          redirect_time=60)

@app.route('/callback/pending')
def callback_pending():
    """Callback para pagamento pendente"""
    print(f"=== [{datetime.now().strftime('%H:%M:%S')}] CALLBACK PENDING CHAMADO ===")
    
    # Parâmetros retornados pelo Mercado Pago
    payment_id = request.args.get('payment_id')
    status = request.args.get('status')
    external_reference = request.args.get('external_reference')
    collection_id = request.args.get('collection_id')
    collection_status = request.args.get('collection_status')
    
    # Se não houver payment_id mas houver collection_id, use collection_id
    if not payment_id and collection_id:
        payment_id = collection_id
    
    # Se não houver payment_id, cria um para referência
    if not payment_id:
        payment_id = external_reference or f"REF_{int(time.time())}"
    
    return render_template('pagamentopendente.html',
                          status=status or "pending",
                          payment_id=payment_id,
                          external_reference=external_reference,
                          mensagem="Pagamento pendente de confirmação. Você receberá uma notificação quando for processado.",
                          redirect_url="/",
                          redirect_time=60)

# ========== WEBHOOK PARA NOTIFICAÇÕES ==========

@app.route('/webhook/mercadopago', methods=['POST'])
def webhook_mercadopago():
    """Webhook para receber notificações do Mercado Pago"""
    print(f"=== [{datetime.now().strftime('%H:%M:%S')}] WEBHOOK RECEBIDO ===")
    
    if request.is_json:
        data = request.get_json()
        print(f"Dados recebidos: {data}")
        
        # Tipo de notificação
        if 'type' in data:
            tipo = data['type']
            print(f"Tipo de notificação: {tipo}")
            
            if tipo == 'payment':
                # Detalhes do pagamento
                payment_id = data.get('data', {}).get('id')
                print(f"Payment ID na notificação: {payment_id}")
                
                # Atualizar status do pedido no banco de dados
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        UPDATE orders 
                        SET status = 'pago' 
                        WHERE payment_id = ? OR external_reference = ?
                    ''', (payment_id, payment_id))
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Status do pedido atualizado para 'pago'")
                    
                except Exception as e:
                    print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Erro ao atualizar status do pedido: {str(e)}")
        
        return jsonify({"status": "received"}), 200
    else:
        print(f"Webhook recebeu dados não JSON")
        return jsonify({"error": "Invalid format"}), 400

# ========== PAINEL DE ADMINISTRAÇÃO ==========

@app.route('/admin')
def admin_panel():
    """Página do painel de administrador"""
    print(f"⚙️ [{datetime.now().strftime('%H:%M:%S')}] Painel admin acessado")
    return render_template('admin.html')

# ========== ROTA DE LOGIN ADMIN (BACKUP/COMPATIBILIDADE) ==========

@app.route('/api/admin/login', methods=['POST', 'OPTIONS'])
def admin_login():
    """Login do administrador - VERSÃO DE COMPATIBILIDADE"""
    if request.method == 'OPTIONS':
        return '', 200  # Responde preflight CORS
    
    try:
        dados = request.get_json()
        
        if not dados:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Dados de login não recebidos")
            return jsonify({
                "success": False,
                "error": "Nenhum dado recebido"
            }), 400
        
        # Compatibilidade com diferentes formatos
        email = dados.get('email', '').strip()
        password = dados.get('password', dados.get('senha', ''))
        
        print(f"🔐 [{datetime.now().strftime('%H:%M:%S')}] Tentativa de login admin via rota específica")
        
        # Verificar se é o email correto
        if email != ADMIN_EMAIL:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Email não autorizado: {email} (esperado: {ADMIN_EMAIL})")
            return jsonify({
                "success": False,
                "error": "Acesso não autorizado"
            }), 401
        
        # Verificar senha usando sistema compatível
        if verificar_admin_senha(password):
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Login admin bem-sucedido via rota específica")
            
            # Gerar token seguro
            token = secrets.token_urlsafe(64)
            
            # Salvar token no banco de dados
            expires_in_hours = 24
            if dados.get('rememberMe', False):
                expires_in_hours = 24 * 7  # 7 dias se "lembrar-me" estiver marcado
            
            save_admin_token(token, email, expires_in_hours)
            
            return jsonify({
                "success": True,
                "message": "Login administrativo realizado com sucesso",
                "token": token,
                "user": {
                    "name": "Administrador",
                    "email": email,
                    "role": "admin"
                },
                "redirect_url": f"/admin/redirect?token={token}",  # URL DE REDIRECIONAMENTO DIRETO
                "expires_in": expires_in_hours * 3600,  # em segundos
                "environment": FLASK_ENV,
                "requires_auth": True
            })
        else:
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Senha incorreta para admin")
            return jsonify({
                "success": False,
                "error": "Senha incorreta"
            }), 401
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro no login admin: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }), 500

# ========== ROTA PARA VERIFICAR TOKEN ADMIN ==========

@app.route('/api/admin/verify', methods=['GET', 'OPTIONS'])
def admin_verify():
    """Verifica se um token de admin é válido"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                "success": False,
                "error": "Token não fornecido"
            }), 401
        
        token = auth_header.replace('Bearer ', '').strip()
        
        # Verificar token no banco de dados
        token_result = verify_admin_token(token)
        
        if token_result["valid"]:
            return jsonify({
                "success": True,
                "valid": True,
                "email": token_result["email"],
                "message": "Token válido",
                "environment": FLASK_ENV
            })
        else:
            return jsonify({
                "success": False,
                "valid": False,
                "error": token_result.get("error", "Token inválido")
            }), 401
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ========== ROTA PARA LOGOUT ADMIN ==========

@app.route('/api/admin/logout', methods=['POST', 'OPTIONS'])
def admin_logout():
    """Logout do administrador - invalida o token"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                "success": False,
                "error": "Token não fornecido"
            }), 401
        
        token = auth_header.replace('Bearer ', '').strip()
        
        # Remover token do banco de dados
        delete_admin_token(token)
        
        return jsonify({
            "success": True,
            "message": "Logout realizado com sucesso"
        })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ========== API DE PRODUTOS DO ADMIN (COM AUTENTICAÇÃO) ==========

@app.route('/api/admin/products', methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])
def api_admin_products():
    """API para gerenciamento de produtos (admin)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # VERIFICAÇÃO DE AUTENTICAÇÃO OBRIGATÓRIA
        if not verificar_autenticacao_admin():
            print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Acesso negado à API admin - Autenticação falhou")
            return jsonify({
                "success": False,
                "error": "Não autorizado. Token de autenticação necessário.",
                "required_auth": True,
                "environment": FLASK_ENV
            }), 401
        
        if request.method == 'GET':
            # Retorna todos os produtos
            produtos_json = gerenciador.to_json()
            print(f"📦 [{datetime.now().strftime('%H:%M:%S')}] API Admin GET: retornando {len(produtos_json)} produtos")
            
            return jsonify({
                "success": True,
                "products": produtos_json,
                "count": len(produtos_json),
                "authenticated": True
            })
        
        elif request.method == 'POST':
            # Adiciona um novo produto
            dados = request.get_json()
            
            print(f"➕ [{datetime.now().strftime('%H:%M:%S')}] API Admin POST: Adicionando novo produto")
            
            # Validação
            campos_obrigatorios = ['name', 'price', 'code', 'category']
            for campo in campos_obrigatorios:
                if campo not in dados or not dados[campo]:
                    print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Campo obrigatório faltando: {campo}")
                    return jsonify({
                        "success": False,
                        "error": f"Campo '{campo}' é obrigatório"
                    }), 400
            
            try:
                price = float(dados['price'])
                if price <= 0:
                    raise ValueError("Preço deve ser maior que zero")
            except (ValueError, TypeError) as e:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Preço inválido: {dados.get('price')} - Erro: {str(e)}")
                return jsonify({
                    "success": False,
                    "error": "Preço inválido"
                }), 400
            
            # Verificar se o código já existe
            codigo_existente = any(p.code == dados['code'] for p in gerenciador.produtos)
            if codigo_existente:
                print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Código já existe: {dados['code']}")
                return jsonify({
                    "success": False,
                    "error": f"Código {dados['code']} já está em uso"
                }), 400
            
            # Gerar ID único
            if gerenciador.produtos:
                novo_id = max([p.id for p in gerenciador.produtos]) + 1
            else:
                novo_id = 1
            
            print(f"🆔 [{datetime.now().strftime('%H:%M:%S')}] Novo ID gerado: {novo_id}")
            
            # Processar imagem padrão se não fornecida
            imagem = dados.get('image', '').strip()
            if not imagem:
                imagem = '/static/images/default-product.jpg'
                print(f"🖼️ [{datetime.now().strftime('%H:%M:%S')}] Usando imagem padrão")
            
            # Processar tamanhos
            sizes_input = dados.get('sizes', '')
            sizes = []
            if sizes_input and isinstance(sizes_input, str):
                sizes = [{"size": s.strip(), "available": True} for s in sizes_input.split(',') if s.strip()]
            elif isinstance(sizes_input, list):
                sizes = sizes_input
            else:
                sizes = [{"size": "Único", "available": True}]
            
            # Processar características
            features_input = dados.get('features', '')
            features = []
            if features_input and isinstance(features_input, str):
                features = [f.strip() for f in features_input.split('\n') if f.strip()]
            elif isinstance(features_input, list):
                features = features_input
            
            # Processar dados de promoção
            on_sale = dados.get('onSale', False)
            original_price = float(dados.get('originalPrice', price))
            discount_percentage = float(dados.get('discountPercentage', 0))
            
            if on_sale and original_price > price and discount_percentage == 0:
                discount_percentage = int(((original_price - price) / original_price) * 100)
            
            # Criar novo produto
            novo_produto = Produto(
                id=novo_id,
                code=dados['code'],
                name=dados['name'],
                price=price,
                image=imagem,
                additional_images=dados.get('additionalImages', []),
                description=dados.get('description', ''),
                features=features,
                category=dados['category'],
                sizes=sizes,
                color=dados.get('color', 'Prata'),
                gender=dados.get('gender', 'feminino'),
                on_sale=on_sale,
                original_price=original_price,
                discount_percentage=discount_percentage,
                stock=int(dados.get('stock', 10)),
                created_at=dados.get('createdAt', datetime.now().isoformat()),
                updated_at=datetime.now().isoformat()
            )
            
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Produto criado: {novo_produto.name} (ID: {novo_id}, Cód: {novo_produto.code}) - R$ {novo_produto.price}")
            
            # Adicionar ao gerenciador
            gerenciador.adicionar_produto(novo_produto)
            
            # Salvar em arquivo JSON
            salvar_produtos_json()
            
            # Log para debug
            print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Total de produtos após adição: {len(gerenciador.produtos)}")
            
            return jsonify({
                "success": True,
                "message": "Produto adicionado com sucesso",
                "product": novo_produto.to_dict(),
                "id": novo_id,
                "authenticated": True
            }), 201
        
        elif request.method == 'PUT':
            # Atualizar produto existente
            dados = request.get_json()
            
            print(f"✏️ [{datetime.now().strftime('%H:%M:%S')}] API Admin PUT recebido para produto ID: {dados.get('id')}")
            
            if 'id' not in dados:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] ID do produto é obrigatório para atualização")
                return jsonify({
                    "success": False,
                    "error": "ID do produto é obrigatório para atualização"
                }), 400
            
            produto_id = dados['id']
            produto = gerenciador.buscar_por_id(produto_id)
            
            if not produto:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Produto não encontrado: ID {produto_id}")
                return jsonify({
                    "success": False,
                    "error": "Produto não encontrado"
                }), 404
            
            print(f"🔄 [{datetime.now().strftime('%H:%M:%S')}] Atualizando produto {produto_id}: {produto.name}")
            
            # Atualizar campos permitidos
            campos_atualizaveis = [
                'name', 'code', 'price', 'image', 'description',
                'features', 'category', 'sizes', 'color', 'gender',
                'onSale', 'originalPrice', 'discountPercentage', 'stock'
            ]
            
            atualizacoes = {}
            for campo in campos_atualizaveis:
                if campo in dados:
                    if campo == 'price' or campo == 'originalPrice':
                        try:
                            atualizacoes[campo] = float(dados[campo])
                        except:
                            print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Erro ao converter {campo}: {dados[campo]}")
                            continue
                    elif campo == 'stock':
                        try:
                            atualizacoes[campo] = int(dados[campo])
                        except:
                            print(f"⚠️ [{datetime.now().strftime('%H:%M:%S')}] Erro ao converter {campo}: {dados[campo]}")
                            continue
                    else:
                        atualizacoes[campo] = dados[campo]
            
            # Aplicar atualizações
            for campo, valor in atualizacoes.items():
                if campo == 'features' and isinstance(valor, str):
                    valor = [f.strip() for f in valor.split('\n') if f.strip()]
                
                if campo == 'sizes' and isinstance(valor, str):
                    valor = [{"size": s.strip(), "available": True} for s in valor.split(',') if s.strip()]
                
                # Mapear nomes de campos
                campo_mapeado = campo
                if campo == 'onSale':
                    campo_mapeado = 'on_sale'
                elif campo == 'originalPrice':
                    campo_mapeado = 'original_price'
                elif campo == 'discountPercentage':
                    campo_mapeado = 'discount_percentage'
                
                if hasattr(produto, campo_mapeado):
                    setattr(produto, campo_mapeado, valor)
                    print(f"   ✅ Campo atualizado: {campo_mapeado} = {valor}")
            
            # Recalcular desconto se necessário
            if produto.on_sale and produto.original_price > produto.price:
                produto.discount_percentage = int(((produto.original_price - produto.price) / produto.original_price) * 100)
                print(f"   ✅ Desconto recalculado: {produto.discount_percentage}%")
            
            # Atualizar data de modificação
            produto.updated_at = datetime.now().isoformat()
            
            # Salvar em arquivo JSON
            salvar_produtos_json()
            
            print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Produto {produto_id} atualizado com sucesso")
            
            return jsonify({
                "success": True,
                "message": "Produto atualizado com sucesso",
                "product": produto.to_dict(),
                "authenticated": True
            })
        
        elif request.method == 'DELETE':
            # Remover produto
            dados = request.get_json()
            
            print(f"🗑️ [{datetime.now().strftime('%H:%M:%S')}] API Admin DELETE recebido: {json.dumps(dados, indent=2)}")
            
            if 'id' not in dados:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] ID do produto é obrigatório para exclusão")
                return jsonify({
                    "success": False,
                    "error": "ID do produto é obrigatório para exclusão"
                }), 400
            
            produto_id = dados['id']
            produto = gerenciador.buscar_por_id(produto_id)
            
            if not produto:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Produto não encontrado para exclusão: ID {produto_id}")
                return jsonify({
                    "success": False,
                    "error": "Produto não encontrado"
                }), 404
            
            print(f"🗑️ [{datetime.now().strftime('%H:%M:%S')}] Removendo produto {produto_id}: {produto.name}")
            
            sucesso = gerenciador.remover_produto(produto_id)
            
            if sucesso:
                # Salvar em arquivo JSON
                salvar_produtos_json()
                
                print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] Produto {produto_id} removido com sucesso")
                print(f"📊 [{datetime.now().strftime('%H:%M:%S')}] Total de produtos após remoção: {len(gerenciador.produtos)}")
                
                return jsonify({
                    "success": True,
                    "message": "Produto removido com sucesso",
                    "authenticated": True
                })
            else:
                print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro ao remover produto {produto_id}")
                return jsonify({
                    "success": False,
                    "error": "Erro ao remover produto"
                }), 500
            
    except Exception as e:
        print(f"❌ [{datetime.now().strftime('%H:%M:%S')}] Erro na API admin: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Erro interno: {str(e)}"
        }), 500

@app.route('/api/admin/stats', methods=['GET', 'OPTIONS'])
def admin_stats():
    """API para estatísticas do admin"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # VERIFICAÇÃO DE AUTENTICAÇÃO
        if not verificar_autenticacao_admin():
            return jsonify({
                "success": False,
                "error": "Não autorizado. Token de autenticação necessário."
            }), 401
        
        produtos_count = len(gerenciador.produtos)
        
        # Calcular valor total dos produtos
        total_value = sum(p.price for p in gerenciador.produtos)
        
        # Contar produtos por categoria
        categorias = {}
        for produto in gerenciador.produtos:
            categoria = produto.category
            categorias[categoria] = categorias.get(categoria, 0) + 1
        
        # Estatísticas do banco de dados
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) as user_count FROM users')
        user_count = cursor.fetchone()['user_count']
        
        cursor.execute('SELECT COUNT(*) as order_count FROM orders')
        order_count = cursor.fetchone()['order_count']
        
        conn.close()
        
        return jsonify({
            "success": True,
            "stats": {
                "total_products": produtos_count,
                "total_value": total_value,
                "categories": categorias,
                "on_sale": len([p for p in gerenciador.produtos if p.on_sale]),
                "low_stock": len([p for p in gerenciador.produtos if getattr(p, 'stock', 0) < 5]),
                "total_users": user_count,
                "total_orders": order_count,
                "frete_gratis_minimo": FRETE_GRATIS_ACIMA if FRETE_GRATIS_ACIMA > 0 else None,
                "frete_padrao": DEFAULT_FRETE
            },
            "authenticated": True
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ========== HEALTH CHECK ==========

@app.route('/health', methods=['GET'])
@app.route('/healthz', methods=['GET'])
def health_check():
    """Endpoint público de verificação de saúde do sistema"""
    try:
        # Verificar componentes básicos
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "flask": "healthy",
                "database": "unknown",
                "mercado_pago": "unknown",
                "produtos": "healthy" if len(gerenciador.produtos) > 0 else "warning",
                "admin_auth": "configured" if ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_HASH != "CONFIGURE_ADMIN_PASSWORD_HASH_IN_ENV" else "not_configured"
            },
            "metrics": {
                "total_produtos": len(gerenciador.produtos),
                "ambiente": FLASK_ENV,
                "admin_email": ADMIN_EMAIL
            }
        }
        
        # Verificar banco de dados
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            conn.close()
            health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = "unhealthy"
            health_status["status"] = "degraded"
        
        # Verificar Mercado Pago (apenas verificação básica)
        if os.environ.get('MP_ACCESS_TOKEN'):
            health_status["components"]["mercado_pago"] = "configured"
        else:
            health_status["components"]["mercado_pago"] = "not_configured"
        
        return jsonify(health_status)
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

# ========== ENDPOINT DE TESTE ==========

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Endpoint para testar a API"""
    return jsonify({
        "status": "online",
        "time": datetime.now().isoformat(),
        "message": "API funcionando corretamente",
        "admin_email": ADMIN_EMAIL,
        "hash_configured": bool(ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_HASH != "CONFIGURE_ADMIN_PASSWORD_HASH_IN_ENV")
    })

# ========== INICIALIZAÇÃO ==========

# Registrar tempo de início para health check
app_start_time = time.time()

if __name__ == '__main__':
    print("=" * 70)
    print(" ROMANEL JOIAS - SISTEMA CONFIGURADO PARA PRODUÇÃO")
    print("=" * 70)
    print(f"🕒 [{datetime.now().strftime('%H:%M:%S')}] Sistema inicializado com {len(gerenciador.produtos)} produtos")
    
    # Porta configurada pelo Render ou padrão
    port = int(os.environ.get("PORT", PORT))
    
    # SEMPRE FALSE em produção
    debug_mode = False
    
    # Verificar se está no Render
    is_render = os.environ.get('RENDER', False)
    
    if is_render:
        print(f"🚀 Ambiente: RENDER (PRODUÇÃO)")
        print(f"🌐 URL externa: {RENDER_EXTERNAL_URL or 'Não configurada'}")
        print(f"🔒 Esquema preferido: {PREFERRED_URL_SCHEME}")
        print(f"🔄 Forçar HTTPS: {'✅ Sim' if FORCE_HTTPS else '❌ Não'}")
        print(f"🔓 Permitir HTTP: {'✅ Sim' if ALLOW_HTTP else '❌ Não'}")
        print(f"🔧 Porta: {port} (Gerenciada automaticamente pelo Render)")
    else:
        print(f"💻 Ambiente: LOCAL (SIMULAÇÃO PRODUÇÃO)")
        print(f"🔧 Porta: {port} (Desenvolvimento local)")
    
    print(f"🐛 Debug: {'❌ DESLIGADO' if not debug_mode else '⚠️ ATENÇÃO: LIGADO EM PRODUÇÃO!'}")
    
    print(f"\n🔐 CONFIGURAÇÕES DE SEGURANÇA:")
    print(f"   Admin email: {ADMIN_EMAIL}")
    print(f"   Admin hash configurado: {'✅ Sim' if ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_HASH != 'CONFIGURE_ADMIN_PASSWORD_HASH_IN_ENV' else '❌ Não (configure no .env)'}")
    print(f"   Token API configurado: {'✅ Sim' if ADMIN_API_TOKEN else '⚠️ Não (usando senha como fallback)'}")
    print(f"   Tokens armazenados no banco: ✅ Sim")
    
    print(f"\n💰 CONFIGURAÇÕES DE NEGÓCIO:")
    print(f"   Frete padrão: R$ {DEFAULT_FRETE:.2f}")
    print(f"   Frete grátis acima de: {'R$ ' + str(FRETE_GRATIS_ACIMA) if FRETE_GRATIS_ACIMA > 0 else '❌ Desativado'}")
    print(f"   Produtos cadastrados: {len(gerenciador.produtos)}")
    
    print(f"\n🌐 URLs IMPORTANTES:")
    print(f"   • Site: http://0.0.0.0:{port}")
    print(f"   • Painel Admin: http://0.0.0.0:{port}/admin")
    print(f"   • API Produtos: http://0.0.0.0:{port}/api/produtos")
    print(f"   • API Login (unificada): http://0.0.0.0:{port}/api/login")
    print(f"   • API Admin Login (backup): http://0.0.0.0:{port}/api/admin/login")
    
    print(f"\n🔑 INSTRUÇÕES DE LOGIN:")
    print(f"   • Usuário comum: Use /api/login com email de usuário")
    print(f"   • Administrador: Use /api/login com email admin ({ADMIN_EMAIL})")
    print(f"   Sistema aceita: senha em texto OU hash SHA256")
    print("=" * 70)

    # IMPORTANTE: Para Render, usar debug=False sempre
    app.run(host="0.0.0.0", port=port, debug=False)