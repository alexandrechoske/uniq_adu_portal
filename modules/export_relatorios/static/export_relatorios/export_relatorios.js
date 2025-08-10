document.addEventListener('DOMContentLoaded',()=>{
  const form = document.getElementById('form-filtros');
  const btnExecutar = document.getElementById('btn-executar');
  const btnExportar = document.getElementById('btn-exportar');
  const statusEl = document.getElementById('consulta-status');
  const theadRow = document.getElementById('thead-row');
  const tbody = document.getElementById('tbody-rows');
  const paginacao = document.getElementById('paginacao');
  const prevBtn = document.getElementById('prev-page');
  const nextBtn = document.getElementById('next-page');
  const currentPageEl = document.getElementById('current-page');
  const totalPagesEl = document.getElementById('total-pages');
  const totalRegistrosEl = document.getElementById('total-registros');

  let lastFilters = {};   // Guarda filtros usados na última busca
  let lastColumns = [];   // Guarda colunas retornadas
  let currentPage = 1;
  let totalPages = 1;
  let pageSize = 500; // default

  function collectFilters(extra={}){
    const fd = new FormData(form);
    const obj = {};
    fd.forEach((v,k)=>{ if(v) obj[k]=v; });
  // older_than_days removido do UI; lógica de datas agora depende somente de date_start/date_end ou identificadores
    Object.assign(obj, extra);
    obj.page = currentPage;
    obj.page_size = pageSize;
    return obj;
  }

  function renderTable(columns, rows){
    // Cabeçalho
    theadRow.innerHTML='';
    columns.forEach(c=>{
      const th=document.createElement('th');
      th.textContent=c.replace('_', ' ').toUpperCase();
      th.setAttribute('data-column', c);
      theadRow.appendChild(th);
    });
    
    // Corpo
    tbody.innerHTML='';
    if(rows.length === 0) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = columns.length;
      td.className = 'p-0 border-0';
      td.innerHTML = `
        <div class="tabela-empty-state">
          <i class="mdi mdi-database-search"></i>
          <h3>Nenhum resultado encontrado</h3>
          <p>Ajuste os filtros de busca ou tente uma consulta diferente para encontrar os dados desejados.</p>
        </div>
      `;
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    
    rows.forEach((r, index)=>{
      const tr=document.createElement('tr');
      columns.forEach(c=>{
        const td=document.createElement('td');
        let val = r[c];
        if(val===null||val===undefined) val='';
        
        // Formatação especial para diferentes tipos de dados
        if(c.includes('valor') && val && !isNaN(val)) {
          val = parseFloat(val).toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
          });
        } else if(c.includes('data') && val) {
          // Manter formato original da data, mas adicionar tooltip se necessário
          td.title = val;
        } else if(c.includes('cnpj') && val) {
          // Formatar CNPJ se necessário
          val = val.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
        }
        
        td.textContent = val;
        td.setAttribute('data-column', c);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }

  async function executarBusca(){
    currentPage = 1; // reset
    await buscarPagina();
  }

  async function buscarPagina(){
    const filtros = collectFilters();
    lastFilters = {...filtros};
    
    // Estado de carregamento
    statusEl.textContent='Consultando...';
    btnExecutar.disabled=true; 
    btnExecutar.classList.add('opacity-50');
    
    // Mostrar indicador de carregamento na tabela
    tbody.innerHTML = `
      <tr>
        <td colspan="100%" class="p-0 border-0">
          <div class="tabela-empty-state">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <h3>Consultando dados...</h3>
            <p>Aguarde enquanto processamos sua solicitação.</p>
          </div>
        </td>
      </tr>
    `;
    
    try{
      const res = await fetch('/export_relatorios/api/search',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-API-Key':window.API_BYPASS_KEY||''},
        body:JSON.stringify(filtros)
      });
      const data = await res.json();
      if(!data.success) throw new Error(data.error||'Erro desconhecido');
      
      statusEl.textContent=`${data.total} registros encontrados em ${data.duration.toFixed(2)}s`; 
      lastColumns = data.columns;
      renderTable(data.columns, data.rows);
      
      // Paginação
      const total = data.total;
      totalPages = Math.max(1, Math.ceil(total / data.page_size));
      currentPageEl.textContent = data.page;
      totalPagesEl.textContent = totalPages;
      totalRegistrosEl.textContent = `${data.returned}/${total}`;
      paginacao.classList.remove('hidden');
      btnExportar.disabled = total === 0;
      if(total > 0) {
        btnExportar.classList.remove('bg-gray-400');
        btnExportar.classList.add('bg-green-600', 'hover:bg-green-700');
        btnExportar.classList.remove('disabled:opacity-50', 'disabled:cursor-not-allowed');
      } else {
        btnExportar.classList.add('bg-gray-400');
        btnExportar.classList.remove('bg-green-600', 'hover:bg-green-700');
        btnExportar.classList.add('disabled:opacity-50', 'disabled:cursor-not-allowed');
      }
    }catch(e){
      statusEl.textContent='Erro: '+e.message;
      // Mostrar erro na tabela
      tbody.innerHTML = `
        <tr>
          <td colspan="100%" class="p-0 border-0">
            <div class="tabela-empty-state">
              <i class="mdi mdi-alert-circle text-red-500"></i>
              <h3 class="text-red-600">Erro na consulta</h3>
              <p class="text-red-500">${e.message}</p>
            </div>
          </td>
        </tr>
      `;
      console.error(e);
    }finally{
      btnExecutar.disabled=false; 
      btnExecutar.classList.remove('opacity-50');
    }
  }

  async function exportarCsv(){
    if(!lastFilters) return;
    statusEl.textContent='Gerando CSV...';
    const filtros = {...lastFilters};
    delete filtros.page; delete filtros.page_size; // exporta tudo dentro do limite server-side
    try{
      const res = await fetch('/export_relatorios/api/export_csv',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-API-Key':window.API_BYPASS_KEY||''},
        body:JSON.stringify(filtros)
      });
      if(!res.ok){
        const js = await res.json().catch(()=>({error:'Erro ao gerar CSV'}));
        throw new Error(js.error||res.statusText);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href=url; a.download=res.headers.get('Content-Disposition')?.split('filename=')[1]||'export.csv';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      statusEl.textContent='CSV pronto.';
    }catch(e){
      statusEl.textContent='Erro exportação: '+e.message;
    }
  }

  btnExecutar?.addEventListener('click', executarBusca);
  prevBtn?.addEventListener('click', async()=>{ if(currentPage>1){ currentPage--; await buscarPagina(); }});
  nextBtn?.addEventListener('click', async()=>{ if(currentPage<totalPages){ currentPage++; await buscarPagina(); }});
  btnExportar?.addEventListener('click', exportarCsv);
});
