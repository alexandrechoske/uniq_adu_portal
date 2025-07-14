"""
Serviço de Cache de Dados
Sistema centralizado para cache de dados do usuário
"""

from datetime import datetime, timedelta
from extensions import supabase
import traceback
from collections import defaultdict

class DataCacheService:
    def __init__(self):
        self.cache = {}
        self.cache_timestamp = {}
        self.cache_duration = 300  # 5 minutos
    
    def get_cache_key(self, user_id, data_type):
        """Gera chave única para o cache"""
        return f"{user_id}_{data_type}"
    
    def is_cache_valid(self, cache_key):
        """Verifica se o cache ainda é válido"""
        if cache_key not in self.cache_timestamp:
            return False
        
        cache_time = self.cache_timestamp[cache_key]
        now = datetime.now()
        return (now - cache_time).seconds < self.cache_duration
    
    def set_cache(self, user_id, data_type, data):
        """Armazena dados no cache"""
        cache_key = self.get_cache_key(user_id, data_type)
        self.cache[cache_key] = data
        self.cache_timestamp[cache_key] = datetime.now()
        print(f"[CACHE] Dados armazenados: {cache_key} - {len(data) if isinstance(data, list) else 'dict'} registros")
    
    def get_cache(self, user_id, data_type):
        """Recupera dados do cache"""
        cache_key = self.get_cache_key(user_id, data_type)
        
        if self.is_cache_valid(cache_key):
            print(f"[CACHE] Cache válido encontrado: {cache_key}")
            return self.cache[cache_key]
        
        print(f"[CACHE] Cache não encontrado ou expirado: {cache_key}")
        return None
    
    def clear_user_cache(self, user_id):
        """Limpa todo o cache de um usuário"""
        keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"{user_id}_")]
        
        for key in keys_to_remove:
            del self.cache[key]
            del self.cache_timestamp[key]
        
        print(f"[CACHE] Cache limpo para usuário: {user_id}")
    
    def preload_user_data(self, user_id, user_role, user_companies=None):
        """Pré-carrega todos os dados do usuário"""
        print(f"[PRELOAD] === INICIANDO PRÉ-CARREGAMENTO ===")
        print(f"[PRELOAD] Usuário: {user_id}, Role: {user_role}")
        print(f"[PRELOAD] Empresas fornecidas: {user_companies}")
        print(f"[PRELOAD] Tipo empresas: {type(user_companies)}")
        
        try:
            # Usar um período mais amplo para garantir que os dados sejam encontrados
            # Buscar dados dos últimos 12 meses para ter certeza de incluir tudo
            data_limite = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
            
            print(f"[PRELOAD] Período: desde {data_limite} (últimos 365 dias)")
            
            # IMPORTANTE: Usar supabase_admin para evitar problemas com RLS
            from extensions import supabase_admin
            
            # Construir query base - buscar todos os dados sem filtro de data inicialmente
            query = supabase_admin.table('importacoes_processos_aberta').select(
                'id, status_processo, canal, data_chegada, '
                'valor_cif_real, cnpj_importador, importador, '
                'modal, data_abertura, mercadoria, data_embarque, '
                'urf_entrada, ref_unique, custo_total, transit_time_real, valor_fob_real'
            ).neq('status_processo', 'Despacho Cancelado')
            
            # Não aplicar filtro de data por enquanto - buscar todos os dados
            # .gte('data_abertura', data_limite)
            
            print(f"[PRELOAD] Query base configurada sem filtro de data")
            
            # Aplicar filtros baseados no role do usuário
            if user_role == 'cliente_unique':
                if not user_companies:
                    print(f"[PRELOAD] Cliente sem empresas - sem dados")
                    self.set_cache(user_id, 'raw_data', [])
                    return []
                
                print(f"[PRELOAD] Filtro empresas cliente: {user_companies}")
                print(f"[PRELOAD] Empresas após normalização: {user_companies}")
                
                # Verificar se há CNPJs na base que batem com as empresas
                sample_query = supabase_admin.table('importacoes_processos_aberta').select('cnpj_importador').limit(10).execute()
                sample_cnpjs = [r['cnpj_importador'] for r in sample_query.data] if sample_query.data else []
                print(f"[PRELOAD] Sample CNPJs na base: {sample_cnpjs[:5]}")
                
                # Aplicar filtro IN para empresas do cliente
                query = query.in_('cnpj_importador', user_companies)
            
            # Executar query
            print(f"[PRELOAD] Executando query...")
            result = query.order('data_abertura', desc=True).execute()
            
            raw_data = result.data if result.data else []
            print(f"[PRELOAD] Dados brutos carregados: {len(raw_data)} registros")
            
            # Log alguns registros para debug
            if raw_data:
                print(f"[PRELOAD] Primeiros 3 CNPJs encontrados: {[r.get('cnpj_importador') for r in raw_data[:3]]}")
            else:
                print(f"[PRELOAD] Nenhum dado encontrado - possível problema de filtro")
            
            # Armazenar dados brutos no cache
            self.set_cache(user_id, 'raw_data', raw_data)
            
            # Pré-processar dados para diferentes views
            self._preprocess_dashboard_data(user_id, raw_data)
            self._preprocess_materiais_data(user_id, raw_data)
            
            print(f"[PRELOAD] === PRÉ-CARREGAMENTO CONCLUÍDO ===")
            return raw_data
            
        except Exception as e:
            print(f"[ERROR PRELOAD] {str(e)}")
            print(f"[ERROR PRELOAD] Traceback: {traceback.format_exc()}")
            return []
    
    def _preprocess_dashboard_data(self, user_id, raw_data):
        """Pré-processa dados para o dashboard"""
        print(f"[PRELOAD] Processando dados do dashboard...")
        
        # Calcular KPIs
        total_processos = len(raw_data)
        total_custo = sum(float(p.get('custo_total', 0) or 0) for p in raw_data)
        
        # Transit time médio
        transit_times = [float(p.get('transit_time_real', 0) or 0) for p in raw_data if float(p.get('transit_time_real', 0) or 0) > 0]
        transit_time_medio = sum(transit_times) / len(transit_times) if transit_times else 0
        
        # Ticket médio
        ticket_medio = total_custo / total_processos if total_processos > 0 else 0
        
        dashboard_kpis = {
            'total_processos': total_processos,
            'total_custo': round(total_custo, 2),
            'transit_time_medio': round(transit_time_medio, 2),
            'ticket_medio': round(ticket_medio, 2)
        }
        
        # Agrupar por modal
        modal_count = defaultdict(int)
        for p in raw_data:
            modal = p.get('modal') or 'N/I'
            modal_count[modal] += 1
        
        dashboard_modais = {
            'labels': list(modal_count.keys()),
            'values': list(modal_count.values())
        }
        
        # Armazenar no cache
        self.set_cache(user_id, 'dashboard_kpis', dashboard_kpis)
        self.set_cache(user_id, 'dashboard_modais', dashboard_modais)
        
        print(f"[PRELOAD] Dashboard processado - {total_processos} processos")
    
    def _preprocess_materiais_data(self, user_id, raw_data):
        """Pré-processa dados para materiais"""
        print(f"[PRELOAD] Processando dados de materiais...")
        
        # Filtrar apenas registros com material
        materiais_data = [p for p in raw_data if p.get('mercadoria') and p.get('mercadoria').strip()]
        
        # Calcular KPIs de materiais
        total_processos = len(materiais_data)
        total_custo = sum(float(p.get('custo_total', 0) or 0) for p in materiais_data)
        
        # Transit time médio
        transit_times = [float(p.get('transit_time_real', 0) or 0) for p in materiais_data if float(p.get('transit_time_real', 0) or 0) > 0]
        transit_time_medio = sum(transit_times) / len(transit_times) if transit_times else 0
        
        # Ticket médio
        ticket_medio = total_custo / total_processos if total_processos > 0 else 0
        
        materiais_kpis = {
            'total_processos': total_processos,
            'total_custo': round(total_custo, 2),
            'transit_time_medio': round(transit_time_medio, 2),
            'ticket_medio': round(ticket_medio, 2)
        }
        
        # Top materiais
        materiais_count = defaultdict(lambda: {'quantidade': 0, 'valor': 0})
        for p in materiais_data:
            material = p.get('mercadoria', '').strip().title()
            if material:
                materiais_count[material]['quantidade'] += 1
                materiais_count[material]['valor'] += float(p.get('valor_cif_real', 0) or 0)
        
        # Ordenar por quantidade
        top_materiais = sorted(
            [(material, data) for material, data in materiais_count.items()],
            key=lambda x: x[1]['quantidade'],
            reverse=True
        )[:10]
        
        top_materiais_chart = {
            'labels': [item[0] for item in top_materiais],
            'values': [item[1]['quantidade'] for item in top_materiais]
        }
        
        # Agrupar por modal
        modal_count = defaultdict(int)
        for p in materiais_data:
            modal = p.get('modal') or 'N/I'
            modal_count[modal] += 1
        
        materiais_modais = {
            'labels': list(modal_count.keys()),
            'values': list(modal_count.values())
        }
        
        # Armazenar no cache
        self.set_cache(user_id, 'materiais_kpis', materiais_kpis)
        self.set_cache(user_id, 'materiais_top', top_materiais_chart)
        self.set_cache(user_id, 'materiais_modais', materiais_modais)
        self.set_cache(user_id, 'materiais_raw', materiais_data[:100])  # Primeiros 100 para tabela
        
        print(f"[PRELOAD] Materiais processados - {total_processos} processos com material")

# Instância global do cache
data_cache = DataCacheService()
