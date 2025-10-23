"""
Script para extrair DDL e dados de exemplo das tabelas RH do Supabase.
Gera documentação em Markdown com estrutura e dados de cada tabela.

Versão simplificada usando apenas API do Supabase (sem psycopg2).

Uso:
    python scripts/extract_rh_tables_simple.py
"""

import os
import sys
from datetime import datetime
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

#Inicializar Flask app para usar supabase
from app import app
with app.app_context():
    from extensions import supabase_admin

def sanitize_value(value):
    """Sanitiza valores sensíveis para documentação."""
    if value is None:
        return 'NULL'
    
    # Converter para string
    str_value = str(value)
    
    # Sanitizar CPF
    if len(str_value) == 11 and str_value.isdigit():
        return f"{str_value[:3]}.***.**{str_value[-2:]}"
    
    # Sanitizar email
    if '@' in str_value:
        parts = str_value.split('@')
        if len(parts) == 2:
            return f"{parts[0][:2]}***@{parts[1]}"
    
    # Sanitizar telefone
    if str_value.replace('(', '').replace(')', '').replace('-', '').replace(' ', '').isdigit():
        return "(11) 9****-****"
    
    return value

def get_sample_data(table_name, limit=3):
    """Busca dados de exemplo de uma tabela."""
    try:
        result = supabase_admin.table(table_name).select('*').limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"⚠️  Erro ao buscar dados de {table_name}: {e}")
        return []

def format_value_for_markdown(value):
    """Formata valores para exibição em Markdown."""
    if value is None:
        return '`NULL`'
    
    if isinstance(value, (dict, list)):
        # JSON formatado
        return f'```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```'
    
    if isinstance(value, bool):
        return f'`{str(value).lower()}`'
    
    if isinstance(value, (int, float)):
        return f'`{value}`'
    
    # String - sanitizar se necessário
    sanitized = sanitize_value(value)
    
    # Se for muito longo, truncar
    str_value = str(sanitized)
    if len(str_value) > 100:
        return f'`{str_value[:100]}...`'
    
    return f'`{str_value}`'

def generate_markdown_documentation():
    """Gera documentação completa em Markdown."""
    
    # Lista completa de tabelas RH
    tables = [
        'rh_acesso_contabilidade',
        'rh_candidatos',
        'rh_cargos',
        'rh_colaborador_contatos_emergencia',
        'rh_colaborador_dependentes',
        'rh_colaboradores',
        'rh_departamentos',
        'rh_eventos_colaborador',
        'rh_historico_colaborador',
        'rh_vagas'
    ]
    
    print(f"📋 Gerando documentação para {len(tables)} tabelas RH...\n")
    
    # Gerar Markdown
    md_content = f"""# 📊 Documentação do Módulo RH - Estrutura de Banco de Dados

**Data de Geração:** {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}  
**Total de Tabelas:** {len(tables)}

> **Nota:** Esta documentação inclui apenas exemplos de dados. Para DDLs completos, consulte os arquivos SQL no diretório `sql/`.

---

## 📋 Índice

"""
    
    # Adicionar índice
    for idx, table in enumerate(tables, 1):
        md_content += f"{idx}. [{table}](#{table.replace('_', '-')})\n"
    
    md_content += "\n---\n\n"
    
    # Processar cada tabela
    for idx, table_name in enumerate(tables, 1):
        print(f"📄 Processando {idx}/{len(tables)}: {table_name}...")
        
        md_content += f"## {idx}. `{table_name}`\n\n"
        
        # Buscar dados de exemplo
        sample_data = get_sample_data(table_name)
        
        # Dados de exemplo
        md_content += "### 💾 Dados de Exemplo\n\n"
        
        if sample_data:
            md_content += f"**Registros encontrados:** Mostrando até {min(len(sample_data), 3)} exemplo(s)\n\n"
            
            # Extrair estrutura das colunas do primeiro registro
            if len(sample_data) > 0:
                md_content += "### 📊 Estrutura das Colunas\n\n"
                md_content += "| Coluna | Tipo Detectado | Exemplo |\n"
                md_content += "|--------|----------------|----------|\n"
                
                first_row = sample_data[0]
                for key, value in first_row.items():
                    tipo = type(value).__name__
                    if isinstance(value, dict):
                        tipo = "JSON Object"
                    elif isinstance(value, list):
                        tipo = "JSON Array"
                    elif value is None:
                        tipo = "null"
                    
                    exemplo = format_value_for_markdown(value)
                    # Truncar exemplo para tabela
                    if len(str(exemplo)) > 50:
                        exemplo = str(exemplo)[:50] + "..."
                    
                    md_content += f"| `{key}` | `{tipo}` | {exemplo} |\n"
                
                md_content += "\n"
            
            # Exemplos completos
            for idx_row, row in enumerate(sample_data, 1):
                md_content += f"#### Exemplo {idx_row}\n\n"
                
                for key, value in row.items():
                    formatted_value = format_value_for_markdown(value)
                    md_content += f"- **{key}:** {formatted_value}\n"
                
                md_content += "\n"
        else:
            md_content += "*Nenhum dado encontrado nesta tabela.*\n\n"
        
        md_content += "---\n\n"
    
    # Salvar arquivo
    output_file = "docs/RH_DATABASE_STRUCTURE.md"
    os.makedirs("docs", exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"\n✅ Documentação gerada com sucesso!")
    print(f"📄 Arquivo: {output_file}")
    print(f"📊 Total de tabelas documentadas: {len(tables)}")

if __name__ == '__main__':
    try:
        generate_markdown_documentation()
    except Exception as e:
        print(f"❌ Erro ao gerar documentação: {e}")
        import traceback
        traceback.print_exc()
