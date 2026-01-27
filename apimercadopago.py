# apimercadopago.py
import mercadopago
import json
import time
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar o SDK do Mercado Pago
# Use variáveis de ambiente para maior segurança
MP_ACCESS_TOKEN = os.environ.get('MP_ACCESS_TOKEN', '')
MP_PUBLIC_KEY = os.environ.get('MP_PUBLIC_KEY', '')
BASE_URL = os.environ.get('RENDER_EXTERNAL_URL', os.environ.get('BASE_URL', ''))
DEFAULT_FRETE = float(os.environ.get('DEFAULT_FRETE', '5.0'))
FRETE_GRATIS_ACIMA = float(os.environ.get('FRETE_GRATIS_ACIMA', '150.0'))
MP_STATEMENT_DESCRIPTOR = os.environ.get('MP_STATEMENT_DESCRIPTOR', 'ROMANEL JOIAS')
MP_BINARY_MODE = os.environ.get('MP_BINARY_MODE', 'True').lower() == 'true'
MP_AUTO_RETURN = os.environ.get('MP_AUTO_RETURN', 'approved')
MP_WEBHOOK_URL = os.environ.get('MP_WEBHOOK_URL', '/webhook/mercadopago')

sdk = mercadopago.SDK(MP_ACCESS_TOKEN) if MP_ACCESS_TOKEN else None

def verificar_ambiente_mercado_pago():
    """Verifica se estamos usando ambiente de produção ou sandbox"""
    print("=" * 60)
    print("VERIFICAÇÃO AMBIENTE MERCADO PAGO")
    print("=" * 60)
    
    print(f"Token configurado: {'✅ Sim' if MP_ACCESS_TOKEN else '❌ Não'}")
    
    if MP_ACCESS_TOKEN:
        token_length = len(MP_ACCESS_TOKEN)
        token_preview = MP_ACCESS_TOKEN[:10] + "..." + MP_ACCESS_TOKEN[-10:] if token_length > 20 else MP_ACCESS_TOKEN
        
        if MP_ACCESS_TOKEN.startswith('APP_USR-'):
            print(f"✅ Ambiente: PRODUÇÃO (token APP_USR-)")
            print(f"   Token: {token_preview}")
            ambiente = "PRODUÇÃO"
        elif MP_ACCESS_TOKEN.startswith('TEST-'):
            print(f"⚠️ Ambiente: SANDBOX/TESTE (token TEST-)")
            print(f"   Token: {token_preview}")
            ambiente = "SANDBOX"
        else:
            print(f"❓ Token com formato desconhecido")
            print(f"   Token: {token_preview}")
            print(f"   Prefixo: {MP_ACCESS_TOKEN[:10]}")
            ambiente = "DESCONHECIDO"
    else:
        print("❌ Token de acesso não configurado!")
        print("   Configure a variável MP_ACCESS_TOKEN no .env ou Render")
        ambiente = "NÃO CONFIGURADO"
    
    print(f"Public Key configurado: {'✅ Sim' if MP_PUBLIC_KEY else '❌ Não'}")
    
    if MP_PUBLIC_KEY:
        pk_preview = MP_PUBLIC_KEY[:10] + "..." + MP_PUBLIC_KEY[-10:] if len(MP_PUBLIC_KEY) > 20 else MP_PUBLIC_KEY
        print(f"   Public Key: {pk_preview}")
    
    print(f"\n📡 URLs do Sistema:")
    print(f"   BASE_URL: {BASE_URL or 'Não configurada'}")
    print(f"   RENDER_EXTERNAL_URL: {os.environ.get('RENDER_EXTERNAL_URL', 'Não configurado')}")
    print(f"   FLASK_ENV: {os.environ.get('FLASK_ENV', 'Não configurado')}")
    
    print(f"\n⚙️ Configurações:")
    print(f"   MP_STATEMENT_DESCRIPTOR: {MP_STATEMENT_DESCRIPTOR}")
    print(f"   MP_BINARY_MODE: {MP_BINARY_MODE}")
    print(f"   MP_AUTO_RETURN: {MP_AUTO_RETURN}")
    print(f"   MP_WEBHOOK_URL: {MP_WEBHOOK_URL}")
    print(f"   Frete padrão: R$ {DEFAULT_FRETE:.2f}")
    print(f"   Frete grátis acima: R$ {FRETE_GRATIS_ACIMA:.2f}")
    
    print("=" * 60)
    
    return MP_ACCESS_TOKEN.startswith('APP_USR-') if MP_ACCESS_TOKEN else False

def testar_conexao_direta():
    """Testa a conexão direta com o Mercado Pago"""
    print("=" * 60)
    print("TESTE DIRETO DE CONEXÃO MERCADO PAGO")
    print("=" * 60)
    
    resultado = {
        "token_configurado": False,
        "token_tipo": "NÃO CONFIGURADO",
        "conexao_sdk": False,
        "conexao_api": False,
        "erro": None,
        "status_code": None
    }
    
    print(f"1. Verificando token...")
    
    if not MP_ACCESS_TOKEN:
        print("❌ ERRO: MP_ACCESS_TOKEN não configurado")
        resultado["erro"] = "Token não configurado"
        return resultado
    
    resultado["token_configurado"] = True
    
    # Determinar tipo de token
    if MP_ACCESS_TOKEN.startswith('APP_USR-'):
        resultado["token_tipo"] = "PRODUÇÃO"
        print("✅ Token de PRODUÇÃO detectado (APP_USR-)")
    elif MP_ACCESS_TOKEN.startswith('TEST-'):
        resultado["token_tipo"] = "SANDBOX"
        print("⚠️ Token de SANDBOX detectado (TEST-)")
    else:
        resultado["token_tipo"] = "DESCONHECIDO"
        print("❓ Formato de token desconhecido")
    
    print(f"2. Inicializando SDK...")
    
    try:
        # Testar inicialização do SDK
        sdk_test = mercadopago.SDK(MP_ACCESS_TOKEN)
        print("✅ SDK inicializado com sucesso")
        resultado["conexao_sdk"] = True
        
        print(f"3. Testando conexão com API...")
        
        # Tentar obter informações da conta (método simples)
        result = sdk_test.payment_methods().list_all()
        
        if result and "status" in result:
            resultado["status_code"] = result.get("status")
            resultado["conexao_api"] = True
            
            if result["status"] == 200:
                print(f"✅ Conexão com API Mercado Pago bem-sucedida!")
                
                # Contar métodos de pagamento disponíveis
                if "response" in result:
                    methods = result["response"]
                    print(f"   Métodos de pagamento disponíveis: {len(methods)}")
                    
                    # Listar alguns métodos
                    for i, method in enumerate(methods[:3]):  # Mostrar apenas 3
                        print(f"   - {method.get('name', 'Desconhecido')} ({method.get('id', 'N/A')})")
                    
                    if len(methods) > 3:
                        print(f"   ... e mais {len(methods) - 3} métodos")
            else:
                print(f"⚠️ API retornou status {result['status']}")
                resultado["erro"] = f"Status {result['status']}"
        else:
            print("❌ Resposta inesperada da API")
            resultado["erro"] = "Resposta inesperada"
            
    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")
        resultado["erro"] = str(e)
    
    print("=" * 60)
    
    if resultado["conexao_api"]:
        print("✅✅✅ TESTE DE CONEXÃO BEM-SUCEDIDO ✅✅✅")
    else:
        print("❌❌❌ TESTE DE CONEXÃO FALHOU ❌❌❌")
    
    print("=" * 60)
    
    return resultado

def verificar_urls_pagamento():
    """Verifica as URLs de pagamento configuradas"""
    print("=" * 60)
    print("VERIFICAÇÃO DE URLs DE PAGAMENTO")
    print("=" * 60)
    
    is_production = verificar_ambiente_mercado_pago()
    
    # URLs de exemplo para teste
    current_base = BASE_URL.rstrip('/') if BASE_URL else ''
    
    print(f"\n📋 URLs configuradas:")
    print(f"   Ambiente: {'PRODUÇÃO' if is_production else 'SANDBOX'}")
    print(f"   URL Base: {current_base or 'URLs relativas'}")
    
    if current_base:
        print(f"\n📍 URLs Absolutas:")
        print(f"   Success: {current_base}/callback/success")
        print(f"   Failure: {current_base}/callback/failure")
        print(f"   Pending: {current_base}/callback/pending")
        print(f"   Webhook: {current_base}{MP_WEBHOOK_URL}")
    else:
        print(f"\n📍 URLs Relativas:")
        print(f"   Success: /callback/success")
        print(f"   Failure: /callback/failure")
        print(f"   Pending: /callback/pending")
        print(f"   Webhook: {MP_WEBHOOK_URL}")
    
    print(f"\n⚙️ Configurações de Redirecionamento:")
    print(f"   Auto Return: {MP_AUTO_RETURN}")
    print(f"   Binary Mode: {MP_BINARY_MODE}")
    print(f"   Statement Descriptor: {MP_STATEMENT_DESCRIPTOR}")
    
    print("=" * 60)
    
    return {
        "ambiente": "PRODUÇÃO" if is_production else "SANDBOX",
        "url_base": current_base,
        "auto_return": MP_AUTO_RETURN
    }

def calcular_frete(total_produtos):
    """Calcula o valor do frete baseado no total da compra"""
    if FRETE_GRATIS_ACIMA > 0 and total_produtos >= FRETE_GRATIS_ACIMA:
        print(f"✅ Frete grátis aplicado (compra acima de R$ {FRETE_GRATIS_ACIMA:.2f})")
        return 0.0
    return DEFAULT_FRETE

def criar_preferencia_pagamento(dados_cliente, carrinho=None, frete_valor=None, request_url=None):
    """
    Cria uma preferência de pagamento no Mercado Pago
    """
    print("=" * 60)
    print("CRIANDO PREFERÊNCIA DE PAGAMENTO")
    print("=" * 60)
    
    # Verificar ambiente primeiro
    is_production = verificar_ambiente_mercado_pago()
    print(f"📋 Dados do Cliente: {dados_cliente}")
    
    # Determinar URL base
    if request_url and not BASE_URL:
        # Extrair URL base da requisição atual
        from urllib.parse import urlparse
        parsed_url = urlparse(request_url)
        current_base = f"{parsed_url.scheme}://{parsed_url.netloc}"
    else:
        current_base = BASE_URL.rstrip('/') if BASE_URL else ''
    
    print(f"\n🌐 Configuração de URLs:")
    print(f"   BASE_URL: {current_base or 'URLs relativas'}")
    print(f"   Ambiente: {'PRODUÇÃO' if is_production else 'SANDBOX/TESTE'}")
    print(f"   Request URL: {request_url or 'Não disponível'}")
    
    # Verificar se o SDK foi inicializado corretamente
    if not sdk:
        error_msg = "SDK do Mercado Pago não inicializado. Verifique o MP_ACCESS_TOKEN."
        print(f"\n❌ ERRO: {error_msg}")
        print("=" * 60)
        return {
            'sucesso': False,
            'error': error_msg,
            'ambiente': 'ERRO'
        }
    
    if not carrinho:
        print("\n⚠️ AVISO: Carrinho vazio, usando produto de teste")
        carrinho = [{
            "id": 1,
            "name": "Anel Aro Duplo Quadrado Banhado Ouro 18k",
            "price": 87.76,
            "quantity": 1,
            "image": "/static/images/default-product.jpg"
        }]
    
    print(f"\n🛒 Carrinho ({len(carrinho)} itens):")
    for i, item in enumerate(carrinho):
        print(f"   {i+1}. {item.get('name', 'Produto')} - R$ {item.get('price', 0):.2f} x {item.get('quantity', 1)}")
    
    items = []
    total_produtos = 0
    
    # Adicionar produtos do carrinho
    for index, item in enumerate(carrinho):
        item_id = str(item.get("id", f"item_{index + 1}"))
        item_title = item.get("name", "Produto")
        item_quantity = int(item.get("quantity", 1))
        item_price = float(item.get("price", 0))
        
        if item_price <= 0:
            item_price = 1.0
        
        total_produtos += item_price * item_quantity
        
        mp_item = {
            "id": item_id,
            "title": item_title[:256],
            "quantity": item_quantity,
            "unit_price": item_price,
            "currency_id": "BRL"
        }
        
        # Converter URL relativa para absoluta se necessário
        if "image" in item and item["image"]:
            if item["image"].startswith('/') and current_base:
                mp_item["picture_url"] = f"{current_base}{item['image']}"
            else:
                mp_item["picture_url"] = item["image"]
        
        items.append(mp_item)
    
    # Calcular frete se não foi fornecido
    if frete_valor is None:
        frete_valor = calcular_frete(total_produtos)
    
    # ADICIONAR FRETE COMO ITEM SEPARADO
    if frete_valor > 0:
        items.append({
            "id": "frete",
            "title": "Frete",
            "quantity": 1,
            "unit_price": frete_valor,
            "currency_id": "BRL",
            "picture_url": f"{current_base}/static/icons/shipping.png" if current_base else ""
        })
        print(f"\n🚚 Frete: R$ {frete_valor:.2f}")
    else:
        print(f"\n🎉 Frete: GRÁTIS!")
    
    total_com_frete = total_produtos + frete_valor
    
    print(f"\n💰 Resumo Financeiro:")
    print(f"   Total produtos: R$ {total_produtos:.2f}")
    print(f"   Frete: R$ {frete_valor:.2f}")
    print(f"   Total com frete: R$ {total_com_frete:.2f}")
    print(f"   Número de itens: {len(items)}")
    
    # Criar um external reference único
    timestamp = int(time.time())
    external_ref = f"pedido_{dados_cliente.get('nome', 'cliente').replace(' ', '_')}_{timestamp}"
    
    # Construir URLs relativas ou absolutas
    if current_base:
        # URLs absolutas
        back_urls = {
            "success": f"{current_base}/callback/success",
            "failure": f"{current_base}/callback/failure", 
            "pending": f"{current_base}/callback/pending"
        }
        notification_url = f"{current_base}{MP_WEBHOOK_URL}" if MP_WEBHOOK_URL.startswith('/') else MP_WEBHOOK_URL
    else:
        # URLs relativas
        back_urls = {
            "success": "/callback/success",
            "failure": "/callback/failure", 
            "pending": "/callback/pending"
        }
        notification_url = MP_WEBHOOK_URL if MP_WEBHOOK_URL.startswith('/') else f"/{MP_WEBHOOK_URL}"
    
    print(f"\n🔗 URLs de Retorno:")
    print(f"   Success: {back_urls['success']}")
    print(f"   Failure: {back_urls['failure']}")
    print(f"   Pending: {back_urls['pending']}")
    print(f"   Webhook: {notification_url}")
    
    # DADOS DA PREFERÊNCIA
    payment_data = {
        "items": items,
        "payer": {
            "name": dados_cliente.get("nome", "Cliente"),
            "email": dados_cliente.get("email", "cliente@example.com"),
            "identification": {
                "type": "CPF",
                "number": dados_cliente.get("cpf", "12345678909")
            }
        },
        # BACK_URLS - URLs para onde o usuário volta APÓS o pagamento
        "back_urls": back_urls,
        # Redirecionamento automático para pagamentos aprovados
        "auto_return": MP_AUTO_RETURN,
        # Configuração para redirecionamento automático
        "payment_methods": {
            "excluded_payment_types": [{"id": "atm"}],
            "installments": 12,
            "default_installments": 1,
            "default_payment_method_id": None
        },
        "statement_descriptor": MP_STATEMENT_DESCRIPTOR,
        "external_reference": external_ref,
        "expires": False,
        "binary_mode": MP_BINARY_MODE,
        "notification_url": notification_url,
        "metadata": {
            "cliente": dados_cliente.get("nome"),
            "email": dados_cliente.get("email"),
            "timestamp": timestamp,
            "frete": frete_valor,
            "total_produtos": total_produtos,
            "total_com_frete": total_com_frete,
            "frete_gratis_minimo": FRETE_GRATIS_ACIMA,
            "ambiente": "PRODUÇÃO" if is_production else "SANDBOX",
            "app": "Romanel Joias"
        }
    }
    
    try:
        print(f"\n📤 Enviando requisição para Mercado Pago...")
        result = sdk.preference().create(payment_data)
        
        print(f"📥 Status da resposta: {result.get('status')}")
        
        if result.get('status') == 201:
            response_data = result.get('response', {})
            
            print(f"\n✅ Preferência criada com sucesso!")
            print(f"   ID: {response_data.get('id')}")
            print(f"   External Reference: {response_data.get('external_reference')}")
            
            init_point = response_data.get('init_point')
            sandbox_init_point = response_data.get('sandbox_init_point')
            
            # **ESSA É A CORREÇÃO CRÍTICA:**
            # Decidir qual URL usar baseado no ambiente
            if is_production:
                # PRODUÇÃO: SEMPRE usar init_point (URL de produção)
                print(f"   ✅ Ambiente: PRODUÇÃO - usando URL de produção")
                url_pagamento = init_point
                if not url_pagamento:
                    print(f"   ⚠️ AVISO: init_point não encontrado para produção!")
                    # Fallback: usar sandbox se produção não estiver disponível
                    url_pagamento = sandbox_init_point
                    if url_pagamento:
                        print(f"   ⚠️ Usando URL sandbox como fallback")
            else:
                # DESENVOLVIMENTO/TESTE: usar sandbox_init_point
                print(f"   ⚠️ Ambiente: SANDBOX/TESTE - usando URL sandbox")
                url_pagamento = sandbox_init_point if sandbox_init_point else init_point
            
            if not url_pagamento:
                print(f"\n❌ ERRO: Nenhuma URL de pagamento encontrada")
                print(f"   init_point: {init_point}")
                print(f"   sandbox_init_point: {sandbox_init_point}")
                print("=" * 60)
                return {
                    'sucesso': False,
                    'error': 'URL de pagamento não encontrada',
                    'ambiente': 'PRODUÇÃO' if is_production else 'SANDBOX'
                }
            
            # Verificar qual URL está sendo usada
            if "sandbox" in url_pagamento.lower():
                print(f"   ⚠️ AVISO: URL SANDBOX detectada!")
                print(f"   💡 Se você está em produção, isso pode ser um problema.")
            else:
                print(f"   ✅ URL de PRODUÇÃO detectada!")
            
            print(f"\n🔗 URL de Pagamento Gerada:")
            print(f"   {url_pagamento}")
            
            print(f"\n📊 Metadados da Preferência:")
            print(f"   Cliente: {dados_cliente.get('nome')}")
            print(f"   Email: {dados_cliente.get('email')}")
            print(f"   Valor Total: R$ {total_com_frete:.2f}")
            print(f"   Itens: {len(carrinho)} produtos + frete")
            
            print("=" * 60)
            print("✅✅✅ PREFERÊNCIA CRIADA COM SUCESSO ✅✅✅")
            print("=" * 60)
            
            return {
                'sucesso': True,
                'url_pagamento': url_pagamento,
                'url_original': url_pagamento,
                'id_preferencia': response_data.get('id'),
                'external_reference': external_ref,
                'frete_valor': frete_valor,
                'total_produtos': total_produtos,
                'total_com_frete': total_com_frete,
                'frete_gratis_aplicado': frete_valor == 0,
                'ambiente': "PRODUÇÃO" if is_production else "SANDBOX",
                'is_production': is_production,
                'response_data': response_data
            }
        else:
            error_msg = f"Status {result.get('status')}: {result.get('response', {})}"
            print(f"\n❌ ERRO Mercado Pago: {error_msg}")
            print("=" * 60)
            return {
                'sucesso': False,
                'error': error_msg,
                'ambiente': 'ERRO'
            }
            
    except Exception as e:
        error_msg = f"Exceção ao criar preferência: {str(e)}"
        print(f"\n❌ EXCEÇÃO: {error_msg}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        
        return {
            'sucesso': False,
            'error': error_msg,
            'ambiente': 'EXCEÇÃO'
        }

def testar_mercado_pago_completo():
    """Teste completo do Mercado Pago"""
    print("=" * 70)
    print("TESTE COMPLETO MERCADO PAGO")
    print("=" * 70)
    
    resultados = {
        "verificacao_ambiente": None,
        "conexao_direta": None,
        "verificacao_urls": None,
        "teste_preferencia": None
    }
    
    # 1. Verificar ambiente
    print("\n1. 🔍 VERIFICANDO AMBIENTE...")
    resultados["verificacao_ambiente"] = verificar_ambiente_mercado_pago()
    
    # 2. Testar conexão direta
    print("\n2. 🔌 TESTANDO CONEXÃO DIRETA...")
    resultados["conexao_direta"] = testar_conexao_direta()
    
    # 3. Verificar URLs
    print("\n3. 🌐 VERIFICANDO URLs...")
    resultados["verificacao_urls"] = verificar_urls_pagamento()
    
    # 4. Testar criação de preferência
    print("\n4. 🧪 TESTANDO CRIAÇÃO DE PREFERÊNCIA...")
    
    dados_cliente_teste = {
        "nome": "Cliente Teste Sistema",
        "email": "teste@romaneljoias.com",
        "cpf": "12345678909"
    }
    
    carrinho_teste = [{
        "id": 999,
        "name": "Produto de Teste Sistema",
        "price": 10.00,
        "quantity": 1,
        "image": "/static/images/default-product.jpg"
    }]
    
    resultado_preferencia = criar_preferencia_pagamento(dados_cliente_teste, carrinho_teste)
    resultados["teste_preferencia"] = resultado_preferencia
    
    # Resumo final
    print("\n" + "=" * 70)
    print("📊 RESUMO DO TESTE")
    print("=" * 70)
    
    token_ok = resultados["conexao_direta"]["token_configurado"] if resultados["conexao_direta"] else False
    conexao_ok = resultados["conexao_direta"]["conexao_api"] if resultados["conexao_direta"] else False
    preferencia_ok = resultados["teste_preferencia"]["sucesso"] if resultados["teste_preferencia"] else False
    
    print(f"✅ Token configurado: {'SIM' if token_ok else 'NÃO'}")
    print(f"✅ Conexão com API: {'SIM' if conexao_ok else 'NÃO'}")
    print(f"✅ Criação de preferência: {'SIM' if preferencia_ok else 'NÃO'}")
    
    if token_ok and conexao_ok and preferencia_ok:
        print("\n🎉🎉🎉 SISTEMA MERCADO PAGO FUNCIONANDO PERFEITAMENTE! 🎉🎉🎉")
        print(f"Ambiente: {resultados['teste_preferencia'].get('ambiente', 'DESCONHECIDO')}")
        
        if resultados["teste_preferencia"].get("url_pagamento"):
            print(f"\n🔗 URL de teste:")
            print(f"{resultados['teste_preferencia']['url_pagamento']}")
    else:
        print("\n⚠️⚠️⚠️ PROBLEMAS DETECTADOS NO SISTEMA! ⚠️⚠️⚠️")
        
        if not token_ok:
            print("❌ Token não configurado ou inválido")
        if not conexao_ok:
            print("❌ Conexão com API Mercado Pago falhou")
        if not preferencia_ok:
            print("❌ Criação de preferência falhou")
    
    print("=" * 70)
    
    return resultados

if __name__ == "__main__":
    print("🚀 INICIANDO TESTE DO MERCADO PAGO")
    print("=" * 70)
    
    # Testar conexão básica primeiro
    test_conexao = testar_conexao_direta()
    
    if test_conexao["conexao_api"]:
        print("\n📋 Deseja executar o teste completo?")
        resposta = input("Digite 'S' para teste completo ou qualquer tecla para sair: ")
        
        if resposta.upper() == 'S':
            resultados = testar_mercado_pago_completo()
            
            # Salvar resultados em arquivo para referência
            with open('teste_mercadopago_resultados.json', 'w', encoding='utf-8') as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)
            
            print("\n📄 Resultados salvos em: teste_mercadopago_resultados.json")
    else:
        print("\n❌ Conexão básica falhou. Não é possível executar teste completo.")
    
    print("\n🏁 Teste concluído!")