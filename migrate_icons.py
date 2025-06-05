#!/usr/bin/env python3
"""
Script de Migração: Conversão de ícones SVG para MDI
Executa a migração v5_migrate_svg_to_mdi_icons.sql diretamente via Supabase
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar variáveis de ambiente
load_dotenv()

def get_supabase_client():
    """Cria e retorna cliente Supabase"""
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            raise Exception("Variáveis SUPABASE_URL e SUPABASE_KEY não encontradas no .env")
        
        supabase: Client = create_client(url, key)
        return supabase
    except Exception as e:
        print(f"❌ Erro ao conectar com Supabase: {e}")
        return None

def execute_migration():
    """Executa a migração dos ícones"""
    print("🚀 Iniciando migração de ícones SVG para MDI...")
    
    # Conectar ao Supabase
    supabase = get_supabase_client()
    if not supabase:
        return False
    
    try:
        # Primeiro, vamos ver o estado atual
        print("\n📊 Estado atual da tabela paginas_portal:")
        current_pages = supabase.table('paginas_portal').select('id_pagina, nome_pagina, icone').execute()
        
        if current_pages.data:
            for page in current_pages.data:
                icon_type = "MDI" if page['icone'].startswith('mdi-') else "SVG" if '<path' in page['icone'] else "OUTRO"
                print(f"  - {page['nome_pagina']} ({page['id_pagina']}): {icon_type}")
        
        print("\n🔄 Executando migração...")
        
        # Migração manual usando updates individuais
        migrations = [
            {
                'id_pagina': 'dashboard',
                'new_icon': 'mdi-view-dashboard',
                'description': 'Dashboard (grid/dashboard)'
            },
            {
                'id_pagina': 'onepage', 
                'new_icon': 'mdi-file-document-multiple',
                'description': 'One Page (documento/página)'
            },
            {
                'id_pagina': 'agente',
                'new_icon': 'mdi-chat',
                'description': 'Agente Unique (chat/conversa)'
            },
            {
                'id_pagina': 'usuarios',
                'new_icon': 'mdi-account-group', 
                'description': 'Usuários (usuários/pessoas)'
            },
            {
                'id_pagina': 'gerenciar_paginas',
                'new_icon': 'mdi-cog',
                'description': 'Gerenciar Páginas (configuração/engrenagem)'
            }
        ]
        
        updated_count = 0
        
        for migration in migrations:
            try:
                # Verificar se a página existe e tem SVG
                existing = supabase.table('paginas_portal').select('icone').eq('id_pagina', migration['id_pagina']).execute()
                
                if existing.data and len(existing.data) > 0:
                    current_icon = existing.data[0]['icone']
                    
                    # Só migrar se for SVG
                    if '<path' in current_icon:
                        result = supabase.table('paginas_portal').update({
                            'icone': migration['new_icon'],
                            'updated_at': 'now()'
                        }).eq('id_pagina', migration['id_pagina']).execute()
                        
                        if result.data:
                            print(f"  ✅ {migration['description']}: {migration['new_icon']}")
                            updated_count += 1
                        else:
                            print(f"  ⚠️  Falha ao migrar {migration['id_pagina']}")
                    else:
                        print(f"  ⏭️  {migration['id_pagina']} já migrado ou não é SVG")
                else:
                    print(f"  ❓ Página {migration['id_pagina']} não encontrada")
                    
            except Exception as e:
                print(f"  ❌ Erro ao migrar {migration['id_pagina']}: {e}")
        
        # Migração de fallback para qualquer SVG restante
        print("\n🔍 Buscando ícones SVG não migrados...")
        remaining_svg = supabase.table('paginas_portal').select('id_pagina, nome_pagina, icone').like('icone', '%<path%').execute()
        
        if remaining_svg.data:
            print(f"📋 Encontrados {len(remaining_svg.data)} ícones SVG para migrar com fallback:")
            for page in remaining_svg.data:
                try:
                    result = supabase.table('paginas_portal').update({
                        'icone': 'mdi-file-document-outline',
                        'updated_at': 'now()'
                    }).eq('id_pagina', page['id_pagina']).execute()
                    
                    if result.data:
                        print(f"  ✅ {page['nome_pagina']}: mdi-file-document-outline (fallback)")
                        updated_count += 1
                    else:
                        print(f"  ❌ Falha ao migrar {page['id_pagina']} (fallback)")
                except Exception as e:
                    print(f"  ❌ Erro ao migrar {page['id_pagina']} (fallback): {e}")
        
        # Verificar resultado final
        print("\n📊 Estado final da tabela paginas_portal:")
        final_pages = supabase.table('paginas_portal').select('id_pagina, nome_pagina, icone').execute()
        
        mdi_count = 0
        svg_count = 0
        
        if final_pages.data:
            for page in final_pages.data:
                if page['icone'].startswith('mdi-'):
                    icon_type = "MDI"
                    mdi_count += 1
                elif '<path' in page['icone']:
                    icon_type = "SVG"
                    svg_count += 1
                else:
                    icon_type = "OUTRO"
                    
                print(f"  - {page['nome_pagina']} ({page['id_pagina']}): {page['icone']} ({icon_type})")
        
        print(f"\n🎉 Migração concluída!")
        print(f"   - Páginas atualizadas: {updated_count}")
        print(f"   - Ícones MDI: {mdi_count}")
        print(f"   - Ícones SVG restantes: {svg_count}")
        
        if svg_count == 0:
            print("✅ Todos os ícones foram migrados com sucesso!")
        else:
            print(f"⚠️  Ainda restam {svg_count} ícones SVG não migrados")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a migração: {e}")
        return False

if __name__ == "__main__":
    try:
        print("=" * 60)
        print("🔄 MIGRAÇÃO DE ÍCONES SVG PARA MDI")
        print("=" * 60)
        
        success = execute_migration()
        
        if success:
            print("\n✅ Migração executada com sucesso!")
            print("💡 Agora você pode:")
            print("   1. Recarregar o cache do menu no navegador (Ctrl+F5)")
            print("   2. Fazer logout e login novamente")
            print("   3. Verificar se os ícones aparecem corretamente")
            sys.exit(0)
        else:
            print("\n❌ Migração falhou!")
            print("🔧 Verifique:")
            print("   1. Conexão com Supabase")
            print("   2. Variáveis de ambiente (.env)")
            print("   3. Permissões de acesso ao banco")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
