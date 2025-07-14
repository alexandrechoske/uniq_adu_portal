# Cache-first Dashboard Implementation
# This file contains the new cache-first dashboard function to replace the current database-heavy approach

from flask import session, jsonify
from routes.auth import login_required, role_required
from permissions import check_permission
import pandas as pd
from datetime import datetime, timedelta
from extensions import supabase

@check_permission()
def dashboard_data_api_cache_first():
    """API endpoint para carregamento de dados do dashboard - Cache First Architecture"""
    try:
        # Verificar cache primeiro (seguindo arquitetura cache-first)
        cached_data = session.get('cached_data')
        
        if cached_data and isinstance(cached_data, list):
            print(f"[DASHBOARD] Usando dados do cache - {len(cached_data)} registros")
            
            # Calcular KPIs a partir do cache
            df = pd.DataFrame(cached_data)
            
            if not df.empty:
                # Preparar dados para análise
                df['data_abertura'] = pd.to_datetime(df['data_abertura'], format='%d/%m/%Y', errors='coerce')
                df['valor_total'] = pd.to_numeric(df.get('valor_total', 0), errors='coerce').fillna(0)
                
                # Filtrar último mês
                hoje = datetime.now()
                inicio_mes = hoje.replace(day=1)
                inicio_mes_anterior = (inicio_mes - timedelta(days=1)).replace(day=1)
                
                df_mes_atual = df[df['data_abertura'] >= inicio_mes]
                df_mes_anterior = df[(df['data_abertura'] >= inicio_mes_anterior) & (df['data_abertura'] < inicio_mes)]
                
                # KPIs calculados do cache
                total_processos = len(df)
                processos_mes_atual = len(df_mes_atual)
                processos_mes_anterior = len(df_mes_anterior)
                valor_total = df['valor_total'].sum()
                valor_mes_atual = df_mes_atual['valor_total'].sum()
                valor_mes_anterior = df_mes_anterior['valor_total'].sum()
                
                # Taxa de crescimento
                if processos_mes_anterior > 0:
                    taxa_crescimento = ((processos_mes_atual - processos_mes_anterior) / processos_mes_anterior) * 100
                else:
                    taxa_crescimento = 0
                
                kpis = {
                    'total_processos': int(total_processos),
                    'processos_periodo': int(processos_mes_atual),
                    'total_valor': float(valor_total),
                    'valor_periodo': float(valor_mes_atual),
                    'media_tempo': 0,  # Seria calculado com mais campos
                    'processos_abertos': int(len(df[df.get('situacao', '') == 'Em andamento'])),
                    'taxa_crescimento': float(taxa_crescimento),
                    'economia_total': 0  # Seria calculado com lógica específica
                }
                
                # Gráficos baseados no cache
                charts = {}
                
                # Evolução Mensal do cache
                df_valid_dates = df.dropna(subset=['data_abertura'])
                if not df_valid_dates.empty:
                    df_monthly = df_valid_dates.groupby(df_valid_dates['data_abertura'].dt.to_period('M')).agg({
                        'numero_di': 'count',
                        'valor_total': 'sum'
                    }).reset_index()
                    
                    charts['monthly'] = {
                        'periods': [str(p) for p in df_monthly['data_abertura']],
                        'processes': df_monthly['numero_di'].tolist(),
                        'values': df_monthly['valor_total'].tolist()
                    }
                else:
                    charts['monthly'] = {'periods': [], 'processes': [], 'values': []}
                
                # Evolução Semanal do cache
                if not df_valid_dates.empty:
                    df_weekly = df_valid_dates.groupby(df_valid_dates['data_abertura'].dt.to_period('W')).agg({
                        'numero_di': 'count',
                        'valor_total': 'sum'
                    }).reset_index().tail(12)  # Últimas 12 semanas
                    
                    charts['weekly'] = {
                        'periods': [str(p) for p in df_weekly['data_abertura']],
                        'processes': df_weekly['numero_di'].tolist(),
                        'values': df_weekly['valor_total'].tolist()
                    }
                else:
                    charts['weekly'] = {'periods': [], 'processes': [], 'values': []}
                
                # Distribuição por Modal
                modal_dist = df['modal'].value_counts().head(10)
                charts['canal'] = {
                    'labels': modal_dist.index.tolist(),
                    'values': modal_dist.values.tolist()
                }
                
                # Top URF Despacho
                urf_dist = df['urf_despacho'].value_counts().head(10)
                charts['urf'] = {
                    'labels': urf_dist.index.tolist(),
                    'values': urf_dist.values.tolist()
                }
                
                # Top Mercadoria
                merc_dist = df['mercadoria'].value_counts().head(10)
                charts['top_material'] = {
                    'labels': merc_dist.index.tolist(),
                    'values': merc_dist.values.tolist()
                }
                
                # Últimas Operações
                df_sorted = df.sort_values('data_abertura', ascending=False)
                charts['latest'] = df_sorted.head(20).to_dict('records')
                
            else:
                # Cache vazio, usar valores padrão
                kpis = {
                    'total_processos': 0, 'processos_periodo': 0, 'total_valor': 0,
                    'valor_periodo': 0, 'media_tempo': 0, 'processos_abertos': 0,
                    'taxa_crescimento': 0, 'economia_total': 0
                }
                charts = {
                    'monthly': {'periods': [], 'processes': [], 'values': []},
                    'weekly': {'periods': [], 'processes': [], 'values': []},
                    'canal': {'labels': [], 'values': []},
                    'urf': {'labels': [], 'values': []},
                    'top_material': {'labels': [], 'values': []},
                    'latest': []
                }
                
        else:
            print("[DASHBOARD] Cache não disponível, usando fallback das views")
            # Fallback para views do banco (mantém funcionamento atual)
            try:
                stats = supabase.table('vw_dashboard_kpis').select('*').limit(1).execute().data
                stats = stats[0] if stats else {}
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar KPIs: {e}")
                stats = {}
            
            kpis = {
                'total_processos': stats.get('total_processos_atual', 0),
                'processos_periodo': stats.get('processos_periodo_anterior', 0),
                'total_valor': stats.get('total_despesas_atual', 0),
                'valor_periodo': stats.get('despesas_periodo_anterior', 0),
                'media_tempo': stats.get('tempo_medio_despacho', 0),
                'processos_abertos': stats.get('processos_abertos', 0),
                'taxa_crescimento': stats.get('taxa_crescimento_despesas', 0),
                'economia_total': stats.get('economia_total', 0)
            }
            
            # Gráficos das views
            charts = {}
            # Evolução Mensal
            try:
                mensal = supabase.table('vw_dashboard_evolucao_mensal')\
                    .select('periodo, total_processos, total_despesas')\
                    .order('periodo').execute().data or []
            except Exception as e:
                print(f"[DASHBOARD] Erro ao buscar evolução mensal: {e}")
                mensal = []
            charts['monthly'] = {
                'periods': [r.get('periodo') for r in mensal],
                'processes': [r.get('total_processos') for r in mensal],
                'values': [r.get('total_despesas') for r in mensal]
            }
            
            # Outras views...
            charts['weekly'] = {'periods': [], 'processes': [], 'values': []}
            charts['canal'] = {'labels': [], 'values': []}
            charts['urf'] = {'labels': [], 'values': []}
            charts['top_material'] = {'labels': [], 'values': []}
            charts['latest'] = []
        
        # Formatação dos valores para exibição
        def format_value_smart(value, currency=False):
            if not value or value == 0:
                return "0"
            try:
                num = float(value)
                if num >= 1_000_000_000:
                    return f"R$ {num/1_000_000_000:.1f}B" if currency else f"{num/1_000_000_000:.1f}B"
                elif num >= 1_000_000:
                    return f"R$ {num/1_000_000:.1f}M" if currency else f"{num/1_000_000:.1f}M"
                elif num >= 1_000:
                    return f"R$ {num/1_000:.1f}K" if currency else f"{num/1_000:.1f}K"
                else:
                    return f"R$ {num:.0f}" if currency else f"{num:.0f}"
            except:
                return "0"
        
        # Aplicar formatação
        for key in kpis:
            if 'valor' in key or 'economia' in key:
                kpis[f"{key}_formatted"] = format_value_smart(kpis[key], currency=True)
            else:
                kpis[f"{key}_formatted"] = format_value_smart(kpis[key])
        
        response_data = {
            'success': True,
            'kpis': kpis,
            'charts': charts,
            'recent_operations': charts.get('latest', [])[:20],
            'cached': cached_data is not None
        }
        
        print(f"[DASHBOARD] Resposta preparada com {len(response_data.get('recent_operations', []))} operações recentes")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"[DASHBOARD] Erro na API dashboard-data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'kpis': {},
            'charts': {},
            'recent_operations': []
        }), 500
