// Mini KPI Popup - Consulta rápida de processos por status
// Usa dados já carregados no dashboard (dashboardData / window.currentOperations)
(function(){
    const STATUS_GROUPS = {
        'processos_abertos': (op, ctx) => {
            const timelineNum = getTimelineNumber(op.status_timeline || op.status_processo || op.status_macro_sistema);
            return timelineNum !== 6; // ≠ 6. Finalizado
        },
        'AG EMBARQUE': (op, ctx) => {
            const timelineNum = getTimelineNumber(op.status_timeline || op.status_processo || op.status_macro_sistema);
            return timelineNum === 1; // 1. Aberto
        },
        'AG CHEGADA': (op, ctx) => {
            const timelineNum = getTimelineNumber(op.status_timeline || op.status_processo || op.status_macro_sistema);
            return timelineNum === 2; // 2. Embarque
        },
        'AG LIBERACAO': (op, ctx) => {
            const timelineNum = getTimelineNumber(op.status_timeline || op.status_processo || op.status_macro_sistema);
            return timelineNum === 3; // 3. Chegada  
        },
        'AGD_ENTREGA': (op, ctx) => {
            const timelineNum = getTimelineNumber(op.status_timeline || op.status_processo || op.status_macro_sistema);
            return [4, 5].includes(timelineNum); // 4. Registro + 5. Desembaraço
        },
        'AG FECHAMENTO': (op, ctx) => {
            const timelineNum = getTimelineNumber(op.status_timeline || op.status_processo || op.status_macro_sistema);
            return timelineNum === 5; // 5. Desembaraço
        },
        'chegando_mes': (op, ctx) => inPeriodoChegada(op, 'mes'),
        'chegando_semana': (op, ctx) => inPeriodoChegada(op, 'semana')
    };

    const TITLE_MAP = {
        'processos_abertos':'Processos Abertos',
        'AG EMBARQUE':'Aguardando Embarque',
        'AG CHEGADA':'Aguardando Chegada',
        'AG LIBERACAO':'Aguardando Liberação',
        'AGD_ENTREGA':'Agd Entrega',
        'AG FECHAMENTO':'Aguardando Fechamento',
        'chegando_mes':'Chegando Este Mês',
        'chegando_semana':'Chegando Esta Semana'
    };

    function getTimelineNumber(status_timeline) {
        // Extrair número do status_timeline (ex: '2. Embarque' -> 2)
        // OU mapear status_processo para número do timeline se status_timeline não existir
        if (!status_timeline) return 0;
        
        // Se status_timeline já é um número com ponto, extrair
        try {
            const match = String(status_timeline).match(/^(\d+)\./);
            if (match) {
                return parseInt(match[1]);
            }
        } catch {}
        
        // Mapear status_processo para timeline number
        const statusProcessoMap = {
            // Estágio 1: Aberto/Aguardando Embarque
            'PROCESSO ABERTO': 1,
            'AGUARDANDO EMBARQUE': 1,
            'MERCADORIA EMBARCADA': 1,
            
            // Estágio 2: Embarque/Em Trânsito
            'EM TRANSITO': 2,
            'EMBARQUE CONFIRMADO': 2,
            'MERCADORIA EM TRANSITO': 2,
            
            // Estágio 3: Chegada
            'CHEGADA CONFIRMADA': 3,
            'MERCADORIA CHEGOU': 3,
            'AGUARDANDO CHEGADA': 3,
            
            // Estágio 4: Registro/DI
            'DECLARACAO REGISTRADA': 4,
            'NUMERARIO ENVIADO': 4,
            'NUMERÁRIO ENVIADO': 4,
            'DI AGUARDANDO PARAMETRIZACAO': 4,
            'DI ALTERADA PELO USUÁRIO': 4,
            'DI ALTERADA PELO USUARIO': 4,
            'PREENCHIMENTO DA DECLARAÇÃO DE IMPORTAÇÃO ESTÁ OK.': 4,
            'PREENCHIMENTO DA DECLARACAO DE IMPORTACAO ESTA OK.': 4,
            'DECLARAÇÃO DE IMPORTAÇÃO NÃO FOI REGISTRADA': 4,
            'DECLARACAO DE IMPORTACAO NAO FOI REGISTRADA': 4,
            
            // Estágio 5: Desembaraço
            'DECLARACAO DESEMBARACADA': 5,
            'DECLARAÇÃO DESEMBARAÇADA': 5,
            'DESEMBARACO AUTORIZADO': 5,
            'DESEMBARAÇO AUTORIZADO': 5,
            
            // Estágio 6: Finalizado
            'PROCESSO FINALIZADO': 6,
            'ENTREGUE': 6,
            'CONCLUIDO': 6,
            'CONCLUÍDO': 6
        };
        
        const normalizedStatus = String(status_timeline).toUpperCase().trim();
        return statusProcessoMap[normalizedStatus] || 0;
    }

    function parseDateBr(str){
        if(!str || typeof str !== 'string') return null;
        const p = str.split('/');
        if(p.length!==3) return null;
        const [d,m,y]=p.map(x=>parseInt(x,10));
        if(!d||!m||!y) return null;
        return new Date(y, m-1, d);
    }

    function inPeriodoChegada(op, tipo){
        const dt = parseDateBr(op.data_chegada);
        if(!dt) return false;
        const hoje = new Date();
        if(tipo==='mes'){
            return dt.getFullYear()===hoje.getFullYear() && dt.getMonth()===hoje.getMonth();
        }
        if(tipo==='semana'){
            // Semana: domingo a sábado
            const day = hoje.getDay(); // 0 domingo
            const inicio = new Date(hoje); inicio.setDate(hoje.getDate()-day);
            const fim = new Date(inicio); fim.setDate(inicio.getDate()+6);
            return dt>=inicio && dt<=fim;
        }
        return false;
    }

    let popupEl = null;
    let lastTrigger = null;

    const PAGE_SIZE = 15;
    let currentPage = 1;
    let currentKey = null;
    let currentList = [];
    let currentSort = { field: 'data_chegada', dir: 'asc' };
    let currentSearch = '';

    function applySearch(list){
        if(!currentSearch) return list;
        const q = currentSearch.toLowerCase();
        return list.filter(op => (op.ref_importador||op.ref_unique||'').toLowerCase().includes(q) || (op.urf_despacho_normalizado||op.urf_despacho||'').toLowerCase().includes(q));
    }

    function sortList(list){
        const {field, dir} = currentSort;
        const mult = dir==='asc'?1:-1;
        return list.slice().sort((a,b)=>{
            let va = (a[field]||'');
            let vb = (b[field]||'');
            // datas dd/mm/yyyy
            if(field.startsWith('data_')){
                const da = parseDateBr(va) || new Date(0);
                const db = parseDateBr(vb) || new Date(0);
                return (da - db)*mult;
            }
            va = (''+va).toLowerCase(); vb=(''+vb).toLowerCase();
            if(va<vb) return -1*mult;
            if(va>vb) return 1*mult;
            return 0;
        });
    }

    function paginate(list){
        const start = (currentPage-1)*PAGE_SIZE;
        return list.slice(start, start+PAGE_SIZE);
    }

    function buildRows(list){
        const filtered = applySearch(list);
        const sorted = sortList(filtered);
        const pageTotal = Math.ceil(filtered.length / PAGE_SIZE) || 1;
        if(currentPage>pageTotal) currentPage = pageTotal;
        const pageItems = paginate(sorted);
        if(!pageItems.length){
            return '<div class="mini-kpi-empty">Nenhum processo encontrado</div>';
        }
        const rows = pageItems.map(op => {
            const pedido = escapeHtml(op.ref_importador || op.ref_unique || op.numero_pedido || 'Sem Info');
            const abertura = escapeHtml(op.data_abertura || 'Sem Info');
            const chegada = escapeHtml(op.data_chegada || 'Sem Info');
            const urf = escapeHtml(op.urf_despacho_normalizado || op.urf_despacho || 'Sem Info');
            return `<tr data-ref="${escapeAttr(op.ref_unique||'')}"><td>${pedido}</td><td>${abertura}</td><td>${chegada}</td><td>${urf}</td></tr>`;
        }).join('');
        return `<div class="mini-kpi-table-wrapper"><table class="mini-kpi-table"><thead><tr>
            <th data-sort="ref_importador">Pedido</th>
            <th data-sort="data_abertura">Abertura</th>
            <th data-sort="data_chegada">Data Chegada</th>
            <th data-sort="urf_despacho_normalizado">URF</th></tr></thead><tbody>${rows}</tbody></table></div>
            ${buildPagination(filtered.length, pageTotal)}`;
    }

    function buildPagination(total, pages){
        if(total<=PAGE_SIZE) return '<div class="mini-kpi-footer"><span>Total: '+total+'</span><span></span></div>';
        let controls = `<div class="mini-kpi-footer"><div>`;
        controls += `<button class="mini-kpi-page-btn" data-page="prev" ${currentPage===1?'disabled':''}>&lt;</button>`;
        controls += `<span class="mini-kpi-page-info">${currentPage}/${pages}</span>`;
        controls += `<button class="mini-kpi-page-btn" data-page="next" ${currentPage===pages?'disabled':''}>&gt;</button>`;
        controls += `</div><span>Total: ${total}</span></div>`;
        return controls;
    }

    function escapeHtml(v){
        return (v==null?'':String(v)).replace(/[&<>"']/g, c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
    }
    function escapeAttr(v){ return escapeHtml(v).replace(/"/g,'&quot;'); }

    function getOperations(){
        if(window.currentOperations && Array.isArray(window.currentOperations) && window.currentOperations.length) return window.currentOperations;
        if(window.dashboardModule && window.dashboardModule.data && Array.isArray(window.dashboardModule.data.operations)) return window.dashboardModule.data.operations;
        // fallback: tentar dashboardData global
        if(window.dashboardData && window.dashboardData.operations) return window.dashboardData.operations;
        return [];
    }

    function filterOperations(key){
        const ops = getOperations();
        const fn = STATUS_GROUPS[key];
        if(!fn) return [];
        try { return ops.filter(o=>fn(o)); } catch(e){ console.warn('[KPI_MINI] Erro filtrando', key, e); return []; }
    }

    function closePopup(){
        if(popupEl){ popupEl.remove(); popupEl=null; lastTrigger=null; }
    }

    function openPopup(trigger){
        const key = trigger.getAttribute('data-mini');
        const list = filterOperations(key);
        currentKey = key; currentList = list; currentPage=1; currentSearch=''; currentSort = {field:'data_chegada',dir:'asc'};
        const title = TITLE_MAP[key] || 'Detalhes';
        if(popupEl && lastTrigger === trigger){ closePopup(); return; }
        closePopup();
        popupEl = document.createElement('div');
        popupEl.className='mini-kpi-popup';
        popupEl.innerHTML = `
            <div class="mini-kpi-popup-header">
                <h4 class="mini-kpi-popup-title">${escapeHtml(title)} <span class="mini-kpi-badge" id="mini-kpi-total">${list.length}</span></h4>
                <div style="display:flex;gap:6px;align-items:center;">
                    <input type="text" id="mini-kpi-search" placeholder="Filtrar..." style="font-size:.6rem;padding:4px 6px;border:1px solid #d0d7de;border-radius:6px;outline:none;" />
                    <button class="mini-kpi-popup-close" aria-label="Fechar">×</button>
                </div>
            </div>
            <div class="mini-kpi-popup-body" id="mini-kpi-body">
                ${buildRows(list)}
            </div>`;
        document.body.appendChild(popupEl);
        positionPopup(trigger, popupEl);
        bindPopupEvents();
        lastTrigger = trigger;
    }

    function rerenderBody(){
        if(!popupEl) return;
        const body = popupEl.querySelector('#mini-kpi-body');
        if(body){ body.innerHTML = buildRows(currentList); }
    }

    function bindPopupEvents(){
        if(!popupEl) return;
        const closeBtn = popupEl.querySelector('.mini-kpi-popup-close');
        if(closeBtn) closeBtn.addEventListener('click', closePopup);
        const searchInput = popupEl.querySelector('#mini-kpi-search');
        if(searchInput){
            searchInput.addEventListener('input', ()=>{ currentSearch = searchInput.value.trim(); currentPage=1; rerenderBody(); attachRowClicks(); attachSortHandlers(); attachPagination(); });
        }
        attachRowClicks();
        attachSortHandlers();
        attachPagination();
    }

    function attachRowClicks(){
        if(!popupEl) return;
        popupEl.querySelectorAll('.mini-kpi-table tbody tr').forEach(tr => {
            tr.addEventListener('click', ()=>{
                const ref = tr.getAttribute('data-ref');
                if(ref){
                    // Encontrar índice na lista global para reusar openProcessModal(index)
                    const ops = getOperations();
                    const idx = ops.findIndex(o=> (o.ref_unique||'') === ref);
                    closePopup();
                    if(idx>=0 && typeof window.openProcessModal === 'function'){
                        window.openProcessModal(idx);
                    }
                }
            });
        });
    }

    function attachSortHandlers(){
        if(!popupEl) return;
        popupEl.querySelectorAll('.mini-kpi-table th[data-sort]').forEach(th=>{
            th.style.cursor='pointer';
            th.addEventListener('click', ()=>{
                const field = th.getAttribute('data-sort');
                if(currentSort.field === field){ currentSort.dir = currentSort.dir==='asc'?'desc':'asc'; } else { currentSort.field = field; currentSort.dir='asc'; }
                rerenderBody();
                attachRowClicks();
                attachSortHandlers();
                attachPagination();
            });
        });
    }

    function attachPagination(){
        if(!popupEl) return;
        popupEl.querySelectorAll('.mini-kpi-page-btn').forEach(btn=>{
            btn.addEventListener('click', ()=>{
                const action = btn.getAttribute('data-page');
                const filtered = applySearch(currentList);
                const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
                if(action==='prev' && currentPage>1) currentPage--;
                if(action==='next' && currentPage<totalPages) currentPage++;
                rerenderBody();
                attachRowClicks();
                attachSortHandlers();
                attachPagination();
            });
        });
    }

    function positionPopup(trigger, popup){
        const rect = trigger.getBoundingClientRect();
        const scrollY = window.scrollY || document.documentElement.scrollTop;
        const scrollX = window.scrollX || document.documentElement.scrollLeft;
        const top = rect.bottom + scrollY + 6;
        let left = rect.left + scrollX - 380 + rect.width; // default right align
        if(left < 8) left = 8;
        const maxLeft = scrollX + window.innerWidth - popup.offsetWidth - 8;
        if(left > maxLeft) left = maxLeft;
        popup.style.top = top + 'px';
        popup.style.left = left + 'px';
    }

    function attach(){
        document.querySelectorAll('.kpi-mini-btn').forEach(btn => {
            if(btn.dataset._miniBound) return; // evitar duplicado
            btn.dataset._miniBound = '1';
            btn.addEventListener('click', e => {
                e.stopPropagation();
                openPopup(btn);
            });
        });
    }

    document.addEventListener('click', (e)=>{
        if(popupEl && !popupEl.contains(e.target)) closePopup();
    });

    window.addEventListener('resize', ()=>{ if(popupEl && lastTrigger) positionPopup(lastTrigger, popupEl); });
    window.addEventListener('scroll', ()=>{ if(popupEl && lastTrigger) positionPopup(lastTrigger, popupEl); }, true);

    document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closePopup(); });

    // Integrar com inicialização existente
    document.addEventListener('DOMContentLoaded', ()=>{
        attach();
        // Re-attach após cargas ou refreshes
        if(window.dashboardModule){
            const originalRefresh = window.dashboardModule.refresh;
            window.dashboardModule.refresh = async function(){
                try { await originalRefresh.apply(this, arguments); } finally { setTimeout(attach, 100); }
            };
        }
    });

    // Expor para debug
    window.kpiMiniPopup = { open: (k)=>{
        const btn = document.querySelector(`.kpi-mini-btn[data-mini="${k}"]`);
        if(btn) openPopup(btn);
    }, close: closePopup, refreshButtons: attach };
})();
