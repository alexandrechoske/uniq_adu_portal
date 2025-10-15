document.addEventListener('DOMContentLoaded',()=>{
  const form = document.getElementById('form-filtros');
  const btnExecutar = document.getElementById('btn-executar');
  const btnExportarExcel = document.getElementById('btn-exportar-excel');
  const btnExportarCsv = document.getElementById('btn-exportar-csv');
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

  // Campos que suportam busca múltipla
  const multiSearchFields = ['ref_importador', 'ref_unique', 'numero_di', 'container'];
  
  // ========== FUNCIONALIDADE DO MODAL DE DOCUMENTOS ==========
  
  const modalOverlay = document.getElementById('modal-documentos');
  const modalClose = document.getElementById('modal-close');
  const modalRefUnique = document.getElementById('modal-ref-unique');
  const modalDocsList = document.getElementById('modal-docs-list');
  const modalLoading = document.getElementById('modal-loading');
  const btnDownloadAllZip = document.getElementById('btn-download-all-zip');
  
  let currentProcessDocs = null;
  let currentRefUnique = null;
  
  function openDocsModal(refUnique, documentos) {
    currentProcessDocs = documentos;
    currentRefUnique = refUnique;
    
    modalRefUnique.textContent = refUnique;
    modalDocsList.innerHTML = '';
    
    documentos.forEach(doc => {
      const docItem = document.createElement('div');
      docItem.className = 'modal-doc-item';
      
      const icon = getFileIcon(doc.extensao);
      
      // Renderizar descrição se existir
      const descricaoHtml = doc.descricao ? 
        `<div class="modal-doc-descricao" title="${doc.descricao}">${doc.descricao}</div>` : '';
      
      docItem.innerHTML = `
        <div class="modal-doc-icon">
          <i class="mdi ${icon}"></i>
        </div>
        <div class="modal-doc-info">
          <div class="modal-doc-name" title="${doc.nome}">${doc.nome}</div>
          ${descricaoHtml}
          <div class="modal-doc-meta">
            <span class="modal-doc-ext">${doc.extensao}</span>
            <span class="modal-doc-size">${formatBytes(doc.tamanho)}</span>
          </div>
        </div>
        <button class="modal-doc-download" title="Baixar documento" data-url="${doc.url}">
          <i class="mdi mdi-download"></i>
        </button>
      `;
      
      modalDocsList.appendChild(docItem);
    });
    
    // Event listener para botões de download individual
    modalDocsList.querySelectorAll('.modal-doc-download').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const url = e.currentTarget.dataset.url;
        if (url && url !== 'null') {
          window.open(url, '_blank');
        }
      });
    });
    
    modalOverlay.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }
  
  function closeDocsModal() {
    modalOverlay.classList.add('hidden');
    document.body.style.overflow = '';
    currentProcessDocs = null;
    currentRefUnique = null;
  }
  
  async function downloadAllAsZip() {
    if (!currentRefUnique) return;
    
    modalLoading.classList.remove('hidden');
    modalDocsList.style.display = 'none';
    
    try {
      const res = await fetch(`/export_relatorios/api/download_all_docs/${encodeURIComponent(currentRefUnique)}`, {
        method: 'GET',
        headers: {'X-API-Key': window.API_BYPASS_KEY || ''}
      });
      
      if (!res.ok) {
        throw new Error('Erro ao gerar ZIP');
      }
      
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${currentRefUnique.replace('/', '-')}_documentos.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      
      closeDocsModal();
    } catch (e) {
      alert('Erro ao baixar documentos: ' + e.message);
    } finally {
      modalLoading.classList.add('hidden');
      modalDocsList.style.display = '';
    }
  }
  
  // Event listeners do modal
  modalClose?.addEventListener('click', closeDocsModal);
  modalOverlay?.addEventListener('click', (e) => {
    if (e.target === modalOverlay) {
      closeDocsModal();
    }
  });
  btnDownloadAllZip?.addEventListener('click', downloadAllAsZip);
  
  // Fechar modal com ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modalOverlay.classList.contains('hidden')) {
      closeDocsModal();
    }
  });
  
  // Adicionar feedback visual para campos de busca múltipla
  multiSearchFields.forEach(fieldName => {
    const input = document.querySelector(`input[name="${fieldName}"]`);
    if (input) {
      input.addEventListener('input', (e) => {
        const value = e.target.value;
        const values = value.split(',').map(v => v.trim()).filter(v => v);
        
        // Remover classes anteriores
        input.classList.remove('border-blue-500', 'border-green-500');
        
        if (values.length > 1) {
          // Múltiplos valores - destacar em verde
          input.classList.add('border-green-500');
          input.title = `${values.length} valores para busca: ${values.join(', ')}`;
        } else if (values.length === 1) {
          // Um valor - destacar em azul
          input.classList.add('border-blue-500');
          input.title = '';
        }
      });
    }
  });

  // Carregar opções dos dropdowns na inicialização
  loadFilterOptions();

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
    const tabelaWrapper = document.getElementById('tabela-wrapper');
    
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
      // Remover classe has-data quando não houver resultados
      tabelaWrapper.classList.remove('has-data');
      
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
    
    // Adicionar classe has-data quando houver resultados
    tabelaWrapper.classList.add('has-data');
    
    rows.forEach((r, index)=>{
      const tr=document.createElement('tr');
      columns.forEach(c=>{
        const td=document.createElement('td');
        let val = r[c];
        if(val===null||val===undefined) val='';
        
        // Formatação especial para coluna de documentos
        if(c === 'documentos') {
          td.className = 'documentos-cell';
          if(Array.isArray(val) && val.length > 0) {
            const docsContainer = document.createElement('div');
            docsContainer.className = 'documentos-container';
            
            // Mostrar apenas os primeiros 3 documentos como badges
            const docsToShow = val.slice(0, 3);
            docsToShow.forEach(doc => {
              const docLink = document.createElement('a');
              docLink.href = doc.url || '#';
              docLink.target = '_blank';
              docLink.rel = 'noopener noreferrer';
              docLink.className = 'documento-badge';
              docLink.title = `${doc.nome} (${formatBytes(doc.tamanho)})`;
              
              // Ícone baseado na extensão
              const icon = getFileIcon(doc.extensao);
              docLink.innerHTML = `
                <i class="mdi ${icon}"></i>
                <span class="documento-nome">${truncateText(doc.nome, 20)}</span>
                <span class="documento-ext">.${doc.extensao}</span>
              `;
              
              docsContainer.appendChild(docLink);
            });
            
            // Badge de contagem se houver muitos documentos - AGORA CLICÁVEL
            if(val.length > 3) {
              const countBadge = document.createElement('span');
              countBadge.className = 'documentos-count-badge';
              countBadge.textContent = `+${val.length - 3}`;
              countBadge.title = `Clique para ver todos os ${val.length} documentos`;
              
              // Armazenar ref_unique e documentos para o modal
              const refUnique = r['ref_unique'];
              countBadge.addEventListener('click', () => {
                openDocsModal(refUnique, val);
              });
              
              docsContainer.appendChild(countBadge);
            }
            
            td.appendChild(docsContainer);
          } else {
            td.innerHTML = '<span class="text-gray-400 text-xs">Sem documentos</span>';
          }
        }
        else if(c === 'url_bandeira') {
          if (val) {
            const img = document.createElement('img');
            img.src = val;
            img.alt = 'Bandeira do país';
            img.style.height = '24px';
            img.style.width = 'auto';
            img.style.borderRadius = '4px';
            td.appendChild(img);
          } else {
            td.innerHTML = '<span class="text-gray-400 text-xs">Sem bandeira</span>';
          }
        }
        else if(c === 'despesas_processo') {
          const despesas = normalizeJsonList(val);
          if (despesas.length > 0) {
            td.innerHTML = `<span class="despesa-badge">${despesas.length} despesa${despesas.length > 1 ? 's' : ''}</span>`;
            td.title = despesas.map(d => `${d.categoria_custo || 'Categoria'}: ${d.valor_custo || '-'} `).join('\n');
          } else {
            td.innerHTML = '<span class="text-gray-400 text-xs">Sem despesas</span>';
          }
        }
        // Formatação especial para diferentes tipos de dados
        else if(c.includes('valor') && val && !isNaN(val)) {
          val = parseFloat(val).toLocaleString('pt-BR', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2
          });
          td.textContent = val;
        } else if(c.includes('data') && val) {
          // Manter formato original da data, mas adicionar tooltip se necessário
          td.title = val;
          td.textContent = val;
        } else if(c.includes('cnpj') && val) {
          // Formatar CNPJ se necessário
          val = val.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');
          td.textContent = val;
        } else {
          td.textContent = val;
        }
        
        td.setAttribute('data-column', c);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  }
  
  // Função auxiliar para formatar bytes
  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  }
  
  // Função auxiliar para obter ícone baseado na extensão
  function getFileIcon(extension) {
    const iconMap = {
      'pdf': 'mdi-file-pdf-box',
      'xml': 'mdi-file-xml-box',
      'xlsx': 'mdi-file-excel-box',
      'xls': 'mdi-file-excel-box',
      'doc': 'mdi-file-word-box',
      'docx': 'mdi-file-word-box',
      'jpg': 'mdi-file-image',
      'jpeg': 'mdi-file-image',
      'png': 'mdi-file-image',
      'zip': 'mdi-folder-zip',
      'rar': 'mdi-folder-zip'
    };
    return iconMap[extension?.toLowerCase()] || 'mdi-file-document';
  }
  
  // Função auxiliar para truncar texto
  function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  }

  function normalizeJsonList(value) {
    if (Array.isArray(value)) return value;
    if (typeof value === 'string' && value.trim()) {
      try {
        const parsed = JSON.parse(value);
        return Array.isArray(parsed) ? parsed : [];
      } catch (e) {
        return [];
      }
    }
    return [];
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
      const res = await fetch('/export_relatorios/api/search_processos',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-API-Key':window.API_BYPASS_KEY||''},
        body:JSON.stringify(filtros)
      });
      const data = await res.json();
      if(!data.success) throw new Error(data.error||'Erro desconhecido');
      
      statusEl.textContent=`${data.total_count} registros encontrados em ${data.duration.toFixed(2)}s`; 
      lastColumns = data.columns;
      renderTable(data.columns, data.rows);
      
      // Paginação
      const total = data.total_count;
      totalPages = Math.max(1, Math.ceil(total / data.page_size));
      currentPageEl.textContent = data.page;
      totalPagesEl.textContent = totalPages;
      totalRegistrosEl.textContent = `${data.returned}/${total}`;
      paginacao.classList.remove('hidden');
      
      // Habilitar/desabilitar ambos os botões de exportação
      btnExportarCsv.disabled = total === 0;
      btnExportarExcel.disabled = total === 0;
      
      if(total > 0) {
        // CSV - Azul
        btnExportarCsv.classList.remove('bg-gray-400');
        btnExportarCsv.classList.add('bg-blue-600', 'hover:bg-blue-700');
        btnExportarCsv.classList.remove('disabled:opacity-50', 'disabled:cursor-not-allowed');
        
        // Excel - Verde
        btnExportarExcel.classList.remove('bg-gray-400');
        btnExportarExcel.classList.add('bg-green-600', 'hover:bg-green-700');
        btnExportarExcel.classList.remove('disabled:opacity-50', 'disabled:cursor-not-allowed');
      } else {
        // CSV
        btnExportarCsv.classList.add('bg-gray-400');
        btnExportarCsv.classList.remove('bg-blue-600', 'hover:bg-blue-700');
        btnExportarCsv.classList.add('disabled:opacity-50', 'disabled:cursor-not-allowed');
        
        // Excel
        btnExportarExcel.classList.add('bg-gray-400');
        btnExportarExcel.classList.remove('bg-green-600', 'hover:bg-green-700');
        btnExportarExcel.classList.add('disabled:opacity-50', 'disabled:cursor-not-allowed');
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

  async function exportarExcel(){
    if(!lastFilters) return;
    statusEl.textContent='Gerando Excel...';
    const filtros = {...lastFilters};
    delete filtros.page; delete filtros.page_size; // exporta tudo dentro do limite server-side
    try{
      const res = await fetch('/export_relatorios/api/export_excel',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-API-Key':window.API_BYPASS_KEY||''},
        body:JSON.stringify(filtros)
      });
      if(!res.ok){
        const js = await res.json().catch(()=>({error:'Erro ao gerar Excel'}));
        throw new Error(js.error||res.statusText);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href=url; a.download=res.headers.get('Content-Disposition')?.split('filename=')[1]||'export.xlsx';
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      statusEl.textContent='Excel pronto.';
    }catch(e){
      statusEl.textContent='Erro exportação: '+e.message;
    }
  }

  // Função para criar skeleton loading
  function createSkeletonLoading() {
    const container = document.getElementById('advanced-filters-container');
    if (!container) return;
    
    // Criar 18 skeleton placeholders (número de campos nos filtros avançados)
    container.innerHTML = '';
    for (let i = 0; i < 18; i++) {
      const skeletonField = document.createElement('div');
      skeletonField.innerHTML = `
        <div class="skeleton-label"></div>
        <div class="skeleton"></div>
      `;
      container.appendChild(skeletonField);
    }
  }

  // Função para restaurar os campos reais
  function restoreAdvancedFilters() {
    const container = document.getElementById('advanced-filters-container');
    if (!container) return;
    
    container.innerHTML = `
      <!-- Modal (Dropdown) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Modal</label>
        <select name="modal" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
          <option value="MARÍTIMA">MARÍTIMA</option>
          <option value="AÉREA">AÉREA</option>
          <option value="RODOVIÁRIA">RODOVIÁRIA</option>
        </select>
      </div>
      
      <!-- Container -->
      <div class="multi-search-field">
        <label class="block text-sm font-medium text-gray-700 mb-1">Container</label>
        <input type="text" name="container" placeholder="CXRU-159.565-5, ..." class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
        <div class="multi-search-hint">💡 Separe múltiplos containers por vírgula</div>
      </div>
      
      <!-- Data Embarque -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Embarque (De)</label>
        <input type="date" name="data_embarque_start" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Embarque (Até)</label>
        <input type="date" name="data_embarque_end" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <!-- Data Chegada -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Chegada (De)</label>
        <input type="date" name="data_chegada_start" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Chegada (Até)</label>
        <input type="date" name="data_chegada_end" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <!-- Data Registro -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Registro (De)</label>
        <input type="date" name="data_registro_start" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Registro (Até)</label>
        <input type="date" name="data_registro_end" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <!-- Data Desembaraço -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Desembaraço (De)</label>
        <input type="date" name="data_desembaraco_start" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Data Desembaraço (Até)</label>
        <input type="date" name="data_desembaraco_end" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <!-- URF/Destino (Dropdown dinâmico) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">URF/Destino</label>
        <select name="urf_despacho" id="select-urf" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
        </select>
      </div>
      
      <!-- Exportador -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Exportador</label>
        <input type="text" name="exportador_fornecedor" placeholder="Nome do exportador" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <!-- Canal (Dropdown) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Canal</label>
        <select name="canal" id="select-canal" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
          <option value="Verde">Verde</option>
          <option value="Amarelo">Amarelo</option>
          <option value="Vermelho">Vermelho</option>
          <option value="Cinza">Cinza</option>
        </select>
      </div>
      
      <!-- Nº DI -->
      <div class="multi-search-field">
        <label class="block text-sm font-medium text-gray-700 mb-1">Nº DI</label>
        <input type="text" name="numero_di" placeholder="25/0000000-0, 25/0000001-1, ..." class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
        <div class="multi-search-hint">💡 Separe múltiplos números por vírgula</div>
      </div>
      
      <!-- Importador -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Importador</label>
        <input type="text" name="importador" placeholder="Nome da empresa" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
      </div>
      
      <!-- Status Sistema (Dropdown dinâmico) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Status Sistema</label>
        <select name="status_sistema" id="select-status-sistema" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
        </select>
      </div>
      
      <!-- Status Timeline (Dropdown dinâmico) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Status Timeline</label>
        <select name="status_timeline" id="select-status-timeline" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
        </select>
      </div>
      
      <!-- País de Procedência (Dropdown dinâmico) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">País de Procedência</label>
        <select name="pais_procedencia" id="select-pais-procedencia" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
        </select>
      </div>
      
      <!-- Mercadoria/Material (Dropdown dinâmico) -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">Mercadoria / Material</label>
        <select name="mercadoria" id="select-mercadoria" class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
          <option value="">Todos</option>
        </select>
      </div>
    `;
  }

  // Função para carregar opções dos dropdowns categóricos
  async function loadFilterOptions() {
    // Mostrar skeleton loading
    createSkeletonLoading();
    
    try {
      const res = await fetch('/export_relatorios/api/filter_options', {
        method: 'GET',
        headers: { 'X-API-Key': window.API_BYPASS_KEY || '' }
      });
      
      if (!res.ok) {
        console.warn('Erro ao carregar opções de filtro:', res.statusText);
        restoreAdvancedFilters();
        return;
      }
      
      const data = await res.json();
      
      // Restaurar campos reais
      restoreAdvancedFilters();
      
      // Popula URF/Destino
      if (data.urf_despacho && data.urf_despacho.values) {
        const selectUrf = document.getElementById('select-urf');
        if (selectUrf) {
          data.urf_despacho.values.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            selectUrf.appendChild(option);
          });
          
          if (data.urf_despacho.limited) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = `... e mais ${data.urf_despacho.count - data.urf_despacho.values.length} opções`;
            selectUrf.appendChild(option);
          }
        }
      }
      
      // Popula Status Sistema
      if (data.status_sistema && data.status_sistema.values) {
        const selectStatusSistema = document.getElementById('select-status-sistema');
        if (selectStatusSistema) {
          data.status_sistema.values.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            selectStatusSistema.appendChild(option);
          });
        }
      }
      
      // Popula Status Timeline
      if (data.status_timeline && data.status_timeline.values) {
        const selectStatusTimeline = document.getElementById('select-status-timeline');
        if (selectStatusTimeline) {
          data.status_timeline.values.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            selectStatusTimeline.appendChild(option);
          });
        }
      }
      
      // Popula País de Procedência
      if (data.pais_procedencia && data.pais_procedencia.values) {
        const selectPais = document.getElementById('select-pais-procedencia');
        if (selectPais) {
          data.pais_procedencia.values.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            selectPais.appendChild(option);
          });
          
          if (data.pais_procedencia.limited) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = `... e mais ${data.pais_procedencia.count - data.pais_procedencia.values.length} opções`;
            selectPais.appendChild(option);
          }
        }
      }
      
      // Popula Mercadoria
      if (data.mercadoria && data.mercadoria.values) {
        const selectMercadoria = document.getElementById('select-mercadoria');
        if (selectMercadoria) {
          data.mercadoria.values.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            selectMercadoria.appendChild(option);
          });
        }
      }
      
      console.log('✅ Opções de filtro carregadas:', data);
    } catch (e) {
      console.error('Erro ao carregar opções de filtro:', e);
      restoreAdvancedFilters();
    }
  }

  btnExecutar?.addEventListener('click', executarBusca);
  prevBtn?.addEventListener('click', async()=>{ if(currentPage>1){ currentPage--; await buscarPagina(); }});
  nextBtn?.addEventListener('click', async()=>{ if(currentPage<totalPages){ currentPage++; await buscarPagina(); }});
  btnExportarCsv?.addEventListener('click', exportarCsv);
  btnExportarExcel?.addEventListener('click', exportarExcel);
});
