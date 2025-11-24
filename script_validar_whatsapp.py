import os
import sys
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuração Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Erro: Variáveis SUPABASE_URL ou SUPABASE_SERVICE_KEY não configuradas no .env")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def validar_numero_whatsapp(numero: str) -> bool:
    """
    Valida se o número está em formato correto para WhatsApp
    Aceita formatos: +55XXXXXXXXXX, 55XXXXXXXXXX, ou XXXXXXXXXX
    """
    # Remove espaços, parênteses e hífens
    numero_limpo = numero.replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
    
    # Verifica se contém apenas dígitos (após remover +)
    numero_limpo = numero_limpo.replace("+", "")
    
    if not numero_limpo.isdigit():
        return False
    
    # WhatsApp Brasil: 55 + DDD (2 dígitos) + número (8 ou 9 dígitos)
    # Total: 11 ou 12 dígitos após o 55, ou 13 ou 14 com +55
    if len(numero_limpo) < 11 or len(numero_limpo) > 14:
        return False
    
    return True


def normalizar_numero(numero: str) -> str:
    """
    Normaliza o número para o formato +55XXXXXXXXXXX
    """
    numero_limpo = numero.replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
    
    # Remove + se existir no início
    if numero_limpo.startswith("+"):
        numero_limpo = numero_limpo[1:]
    
    # Se não tiver código de país, adiciona
    if not numero_limpo.startswith("55"):
        numero_limpo = "55" + numero_limpo
    
    return "+" + numero_limpo


def buscar_empresas_por_whatsapp(numero: str) -> dict:
    """
    Busca todas as empresas atreladas a um número de WhatsApp
    """
    print(f"\n🔍 Buscando informações para: {numero}")
    print("=" * 70)
    
    # Valida número
    if not validar_numero_whatsapp(numero):
        print(f"❌ Número inválido: {numero}")
        print("   Formato esperado: +55XX9XXXX-XXXX ou 55XX9XXXXXX ou XXXXXXXXXX")
        return {"valido": False, "numero_original": numero}
    
    numero_normalizado = normalizar_numero(numero)
    print(f"✅ Número validado: {numero_normalizado}")
    print("=" * 70)
    
    resultados = {
        "valido": True,
        "numero_original": numero,
        "numero_normalizado": numero_normalizado,
        "user_whatsapp": [],
        "clientes_agentes": [],
        "usuarios_info": [],
        "resumo": {}
    }
    
    try:
        # ========================================
        # 1. Buscar em user_whatsapp
        # ========================================
        print("\n📱 Buscando em user_whatsapp...")
        response_uw = supabase.table("user_whatsapp").select(
            "id, user_id, numero, nome, tipo, principal, ativo, created_at"
        ).ilike("numero", f"%{numero_normalizado}%").execute()
        
        if response_uw.data:
            print(f"   ✅ Encontrado(s) {len(response_uw.data)} registro(s)")
            resultados["user_whatsapp"] = response_uw.data
            
            for reg in response_uw.data:
                print(f"   - ID: {reg['id']}")
                print(f"     Nome: {reg['nome']}")
                print(f"     Número: {reg['numero']}")
                print(f"     Tipo: {reg['tipo']}")
                print(f"     Principal: {reg['principal']}")
                print(f"     Ativo: {reg['ativo']}")
        else:
            print("   ❌ Nenhum registro encontrado")
        
        # ========================================
        # 2. Buscar em clientes_agentes
        # ========================================
        print("\n👥 Buscando em clientes_agentes...")
        response_ca = supabase.table("clientes_agentes").select(
            "id, user_id, nome, numero, empresa, usuario_ativo, created_at, updated_at"
        ).execute()
        
        clientes_agentes_encontrados = []
        if response_ca.data:
            for reg in response_ca.data:
                if reg.get("numero") and isinstance(reg["numero"], list):
                    for num in reg["numero"]:
                        if numero_normalizado in str(num) or numero in str(num):
                            clientes_agentes_encontrados.append(reg)
                            break
                elif numero_normalizado in str(reg.get("numero", "")) or numero in str(reg.get("numero", "")):
                    clientes_agentes_encontrados.append(reg)
        
        if clientes_agentes_encontrados:
            print(f"   ✅ Encontrado(s) {len(clientes_agentes_encontrados)} registro(s)")
            resultados["clientes_agentes"] = clientes_agentes_encontrados
            
            for reg in clientes_agentes_encontrados:
                print(f"   - ID: {reg['id']}")
                print(f"     Nome: {reg['nome']}")
                print(f"     Números: {reg['numero']}")
                print(f"     Empresas: {reg['empresa']}")
                print(f"     Ativo: {reg['usuario_ativo']}")
        else:
            print("   ❌ Nenhum registro encontrado")
        
        # ========================================
        # 3. Buscar informações dos usuários
        # ========================================
        user_ids = set()
        for reg in resultados["user_whatsapp"]:
            if reg.get("user_id"):
                user_ids.add(reg["user_id"])
        for reg in resultados["clientes_agentes"]:
            if reg.get("user_id"):
                user_ids.add(reg["user_id"])
        
        if user_ids:
            print(f"\n👤 Buscando informações de {len(user_ids)} usuário(s)...")
            for user_id in user_ids:
                # Buscar em users
                response_user = supabase.table("users").select(
                    "id, name, email, role, is_active, empresa_controladora_id"
                ).eq("id", user_id).execute()
                
                if response_user.data:
                    user_data = response_user.data[0]
                    resultados["usuarios_info"].append(user_data)
                    print(f"   ✅ ID: {user_data['id']}")
                    print(f"      Nome: {user_data['name']}")
                    print(f"      Email: {user_data['email']}")
                    print(f"      Role: {user_data['role']}")
                    print(f"      Ativo: {user_data['is_active']}")
                    
                    # Buscar empresas do usuário
                    response_ue = supabase.table("user_empresas").select(
                        "id, cliente_sistema_id, ativo, data_vinculo"
                    ).eq("user_id", user_id).execute()
                    
                    if response_ue.data:
                        print(f"      Empresas atreladas:")
                        for empresa_assoc in response_ue.data:
                            # Buscar dados da empresa
                            response_cliente = supabase.table("cad_clientes_sistema").select(
                                "id, nome_cliente, cnpjs, ativo"
                            ).eq("id", empresa_assoc["cliente_sistema_id"]).execute()
                            
                            if response_cliente.data:
                                empresa = response_cliente.data[0]
                                print(f"        - {empresa['nome_cliente']}")
                                print(f"          ID: {empresa['id']}")
                                print(f"          CNPJs: {empresa['cnpjs']}")
                                print(f"          Ativo: {empresa['ativo']}")
                                print(f"          Vinculado em: {empresa_assoc['data_vinculo']}")
    
    except Exception as e:
        print(f"❌ Erro ao buscar dados: {str(e)}")
        resultados["erro"] = str(e)
    
    # ========================================
    # RESUMO
    # ========================================
    print("\n" + "=" * 70)
    print("📊 RESUMO")
    print("=" * 70)
    print(f"Número Original: {numero}")
    print(f"Número Normalizado: {numero_normalizado}")
    print(f"Válido: {'✅ Sim' if resultados['valido'] else '❌ Não'}")
    print(f"Registros em user_whatsapp: {len(resultados['user_whatsapp'])}")
    print(f"Registros em clientes_agentes: {len(resultados['clientes_agentes'])}")
    print(f"Usuários encontrados: {len(resultados['usuarios_info'])}")
    
    return resultados


if __name__ == "__main__":
    # Exemplo de uso
    if len(sys.argv) > 1:
        numero = sys.argv[1]
    else:
        # Usar número padrão para teste
        numero = "+5547992781548"  # Edgar - Águas Azuis (número corrigido)
        print(f"⚠️  Nenhum número fornecido. Usando padrão: {numero}")
        print("   Uso: python script_validar_whatsapp.py '+55XXXXXXXXXX'")
    
    resultado = buscar_empresas_por_whatsapp(numero)
