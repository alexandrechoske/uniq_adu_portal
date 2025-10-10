"""
=============================================================
GERENCIADOR DO MODO DE MANUTENÇÃO
=============================================================
Script utilitário para ativar/desativar o modo de manutenção
de forma rápida e fácil.

USO:
    python gerenciar_manutencao.py [ativar|desativar|status]

EXEMPLOS:
    python gerenciar_manutencao.py ativar
    python gerenciar_manutencao.py desativar
    python gerenciar_manutencao.py status
=============================================================
"""

import sys
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def print_header():
    """Imprime o cabeçalho do script"""
    print("\n" + "="*70)
    print("  🔧 GERENCIADOR DE MODO DE MANUTENÇÃO - Portal UniSystem")
    print("="*70 + "\n")

def get_current_status():
    """Obtém o status atual do modo de manutenção"""
    try:
        from extensions import supabase_admin
        
        response = supabase_admin.table('DANGER_TABLE_MANUTENCAO')\
            .select('*')\
            .eq('id', '1')\
            .single()\
            .execute()
        
        if response.data:
            return response.data
        return None
    except Exception as e:
        print(f"❌ Erro ao consultar status: {e}")
        return None

def show_status():
    """Mostra o status atual do modo de manutenção"""
    print("📊 CONSULTANDO STATUS ATUAL...\n")
    
    data = get_current_status()
    
    if not data:
        print("❌ Não foi possível consultar o status da manutenção")
        print("   Verifique se a tabela DANGER_TABLE_MANUTENCAO existe no Supabase")
        return
    
    em_manutencao = data.get('manutencao', False)
    
    print(f"Status: {'🔴 EM MANUTENÇÃO' if em_manutencao else '🟢 OPERACIONAL'}")
    print(f"Última atualização: {data.get('updated_at', 'N/A')}")
    print(f"Atualizado por: {data.get('updated_by', 'N/A')}")
    
    if em_manutencao:
        print(f"\n⚠️  PORTAL BLOQUEADO - Usuários não podem fazer login")
        
        if data.get('mensagem_customizada'):
            print(f"\nMensagem exibida aos usuários:")
            print(f"   '{data.get('mensagem_customizada')}'")
        
        if data.get('data_prevista_fim'):
            print(f"\nPrevisão de término: {data.get('data_prevista_fim')}")
    else:
        print(f"\n✅ PORTAL FUNCIONANDO NORMALMENTE")

def ativar_manutencao(mensagem=None, horas=2):
    """Ativa o modo de manutenção"""
    print("🔧 ATIVANDO MODO DE MANUTENÇÃO...\n")
    
    # Verificar status atual
    current = get_current_status()
    if current and current.get('manutencao'):
        print("⚠️  O portal já está em modo de manutenção!")
        print("   Use 'desativar' para liberar o acesso\n")
        return
    
    # Mensagem padrão se não fornecida
    if not mensagem:
        mensagem = "Portal em manutenção programada. Estamos realizando melhorias para oferecer uma experiência ainda melhor. Agradecemos sua compreensão!"
    
    # Calcular previsão de término
    data_prevista = (datetime.now() + timedelta(hours=horas)).isoformat()
    
    try:
        from extensions import supabase_admin
        
        response = supabase_admin.table('DANGER_TABLE_MANUTENCAO')\
            .update({
                'manutencao': True,
                'mensagem_customizada': mensagem,
                'data_inicio': datetime.now().isoformat(),
                'data_prevista_fim': data_prevista,
                'updated_at': datetime.now().isoformat(),
                'updated_by': 'gerenciar_manutencao.py'
            })\
            .eq('id', '1')\
            .execute()
        
        if response.data:
            print("✅ MODO DE MANUTENÇÃO ATIVADO COM SUCESSO!\n")
            print("🔴 Portal agora está BLOQUEADO")
            print("   • Usuários não conseguem fazer login")
            print("   • Página de manutenção será exibida")
            print(f"   • Previsão de término: {horas}h ({data_prevista})")
            print(f"\n💬 Mensagem exibida:\n   '{mensagem}'")
            print("\n⚠️  Para liberar o portal, execute:")
            print("   python gerenciar_manutencao.py desativar\n")
        else:
            print("❌ Erro ao ativar modo de manutenção")
    
    except Exception as e:
        print(f"❌ Erro: {e}\n")

def desativar_manutencao():
    """Desativa o modo de manutenção"""
    print("✅ DESATIVANDO MODO DE MANUTENÇÃO...\n")
    
    # Verificar status atual
    current = get_current_status()
    if current and not current.get('manutencao'):
        print("✅ O portal já está operacional!")
        print("   Nenhuma ação necessária\n")
        return
    
    try:
        from extensions import supabase_admin
        
        response = supabase_admin.table('DANGER_TABLE_MANUTENCAO')\
            .update({
                'manutencao': False,
                'mensagem_customizada': None,
                'updated_at': datetime.now().isoformat(),
                'updated_by': 'gerenciar_manutencao.py'
            })\
            .eq('id', '1')\
            .execute()
        
        if response.data:
            print("✅ MODO DE MANUTENÇÃO DESATIVADO COM SUCESSO!\n")
            print("🟢 Portal agora está OPERACIONAL")
            print("   • Usuários podem fazer login normalmente")
            print("   • Sistema funcionando 100%\n")
        else:
            print("❌ Erro ao desativar modo de manutenção")
    
    except Exception as e:
        print(f"❌ Erro: {e}\n")

def show_help():
    """Mostra a ajuda do script"""
    print("""
USO: python gerenciar_manutencao.py [comando]

COMANDOS DISPONÍVEIS:

  status       Mostra o status atual do modo de manutenção
  
  ativar       Ativa o modo de manutenção
               - Bloqueia acesso ao portal
               - Exibe página de manutenção aos usuários
  
  desativar    Desativa o modo de manutenção
               - Libera acesso ao portal
               - Usuários podem fazer login normalmente

EXEMPLOS:

  python gerenciar_manutencao.py status
  python gerenciar_manutencao.py ativar
  python gerenciar_manutencao.py desativar

DICAS:

  • Sempre verifique o status antes de ativar/desativar
  • Use mensagens claras para informar os usuários
  • Defina previsões realistas de tempo de manutenção
    """)

def main():
    """Função principal"""
    print_header()
    
    if len(sys.argv) < 2:
        print("❌ Comando não especificado!\n")
        show_help()
        return
    
    comando = sys.argv[1].lower()
    
    if comando == 'status':
        show_status()
    elif comando == 'ativar':
        ativar_manutencao()
    elif comando == 'desativar':
        desativar_manutencao()
    elif comando in ['help', 'ajuda', '-h', '--help']:
        show_help()
    else:
        print(f"❌ Comando '{comando}' não reconhecido!\n")
        show_help()
    
    print("="*70 + "\n")

if __name__ == '__main__':
    main()
