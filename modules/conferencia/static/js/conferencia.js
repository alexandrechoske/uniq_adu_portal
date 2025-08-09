const form = document.getElementById('uploadForm');
const statusDiv = document.getElementById('status');
const previewDiv = document.getElementById('preview');
const jsonDiv = document.getElementById('jsonResult');
const painelEstruturado = document.getElementById('resultadoEstruturado');
const resumoDiv = document.getElementById('resumo');
const camposDiv = document.getElementById('campos');
const itensDiv = document.getElementById('itens');
let lastCamposData = null;
let lastItensData = null;
let currentFilterMode = 'all';

const REGULATORIOS = new Set(['invoice_number','issue_date','incoterm','seller_exporter','buyer_consignee','gross_weight','net_weight','payment_terms','exporter_reference']);

const TOOLTIP_STATUS = 'Status das cores: Verde=OK (campo presente e confiança >=65%), Amarelo=atenção (campo presente mas baixa confiança <65%), Vermelho=ausente (não encontrado). Campos regulatórios são obrigatórios conforme escopo inicial.';

function pillStatus(valorExtraido, confidence){
  if(!valorExtraido){
    return 'erro';
  }
  if(confidence === undefined || confidence === null) return 'ok';
  return confidence < 0.65 ? 'alerta' : 'ok';
}

function esc(v){
  if(v===null || v===undefined) return '';
  return String(v).replace(/[&<>]/g, s=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[s]));
}

function buildCounts(campos){
  let ok=0, alerta=0, erro=0, regsFaltando=[];
  Object.entries(campos).forEach(([k,c])=>{
    const ve = c?.valor_extraido ?? null;
    const st = pillStatus(ve, c?.confidence);
    if(st==='ok') ok++; else if(st==='alerta') alerta++; else erro++;
    if(REGULATORIOS.has(k) && !ve) regsFaltando.push(k);
  });
  return {ok, alerta, erro, regsFaltando};
}

function renderCampos(campos){
  lastCamposData = campos;
  camposDiv.innerHTML = '';
  const ordem = [
    'invoice_number','issue_date','seller_exporter','buyer_consignee','exporter_reference','payment_terms','incoterm','gross_weight','net_weight','currency','country_of_origin','country_of_acquisition'
  ];
  const counts = buildCounts(campos);
  const countsBar = document.createElement('div');
  countsBar.className = 'counts';
  countsBar.innerHTML = `
    <span class='c-ok'>OK: ${counts.ok}</span>
    <span class='c-alerta'>Atenção: ${counts.alerta}</span>
    <span class='c-erro'>Ausente: ${counts.erro}</span>
    <span>Regulatórios faltando: ${counts.regsFaltando.length}</span>
    <span class='tooltip'>?<span class='tip'>${esc(TOOLTIP_STATUS)}</span></span>
  `;
  camposDiv.appendChild(countsBar);
  const filterBar = document.createElement('div');
  filterBar.className = 'filter-bar';
  filterBar.innerHTML = `Mostrar: <button data-f="all" class='${currentFilterMode==='all'?'active':''}'>Todos</button><button data-f="issues" class='${currentFilterMode==='issues'?'active':''}'>Somente Problemas</button><button data-f="reg" class='${currentFilterMode==='reg'?'active':''}'>Regulatórios</button>`;
  camposDiv.appendChild(filterBar);
  filterBar.addEventListener('click', (e)=>{
    if(e.target.tagName==='BUTTON'){
      currentFilterMode = e.target.getAttribute('data-f');
      renderCampos(lastCamposData); // re-render
    }
  });
  ordem.forEach(k=>{
    const c = campos[k] || {};
    const ve = c.valor_extraido ?? c.valor ?? null;
    const conf = c.confidence ?? null;
    const status = pillStatus(ve, conf);
    // filter logic
    if(currentFilterMode==='issues' && status==='ok') return;
    if(currentFilterMode==='reg' && !REGULATORIOS.has(k)) return;
    const normKeys = Object.keys(c).filter(x=>x.endsWith('_norm'));
    let normLine = '';
    if(normKeys.length){
      normLine = normKeys.map(nk=>`${nk}: ${esc(c[nk])}`).join(' | ');
    }
    const snippet = c.source_snippet ? `<span class=\"snippet\">${esc(c.source_snippet)}</span>` : '';
    const badgeReg = REGULATORIOS.has(k) ? '<span class="badge reg" title="Campo regulatório">REG</span>' : '';
    const anchorId = 'campo_'+k;
    camposDiv.insertAdjacentHTML('beforeend', `
      <div class="campo-row" id="${anchorId}">
        <div class="campo-nome"><span class="pill ${status}"></span>${esc(k)} ${badgeReg}</div>
        <div class="campo-valor">
          <strong>${esc(ve)||'<i>não encontrado</i>'}</strong>
          ${conf!==null?`<span class="score">(${(conf*100).toFixed(0)}%)</span>`:''}
          ${normLine?`<div class="tiny">${normLine}</div>`:''}
          ${snippet}
        </div>
      </div>`);
  });
  // Provide quick anchor link in resumo if first issue
  const firstIssue = Array.from(camposDiv.querySelectorAll('.campo-row')).find(r=>!r.querySelector('.pill.ok'));
  if(firstIssue){
    const link = document.createElement('span');
    link.className = 'anchor-link';
    link.textContent = 'Ir para primeiro problema';
    link.onclick = ()=> firstIssue.scrollIntoView({behavior:'smooth', block:'center'});
    camposDiv.insertBefore(link, camposDiv.children[1]);
  }
}

function renderItens(itens){
  if(!Array.isArray(itens) || !itens.length){
    itensDiv.innerHTML = '<em>Nenhum item identificado.</em>';
    return;
  }
  let html = '<table class="itens-table"><thead><tr><th>#</th><th>Descrição</th><th>Qtd</th><th>Preço Unit.</th><th>Total Item</th><th>Conf.</th></tr></thead><tbody>';
  itens.forEach((it, idx)=>{
    const desc = it.descricao_completa || it.descricao || {};
    const qtd = it.quantidade_unidade || {};
    const pu = it.preco_unitario || {};
    const tot = it.valor_total_item || {};
    const st = pillStatus(desc.valor_extraido || desc.valor, desc.confidence);
    html += `<tr>
      <td><span class="pill ${st}"></span>${idx+1}</td>
      <td>${esc(desc.valor_extraido||desc.valor||'')}</td>
      <td>${esc(qtd.valor_extraido||'')}<div class="tiny">${qtd.qty_norm||''} ${qtd.unit_norm||''}</div></td>
      <td>${esc(pu.valor_extraido||'')}<div class="tiny">${pu.unit_price_norm||''}</div></td>
      <td>${esc(tot.valor_extraido||'')}<div class="tiny">${tot.amount_norm||''}</div></td>
      <td class="tiny">${desc.confidence? (desc.confidence*100).toFixed(0)+'%':''}</td>
    </tr>`;
  });
  html += '</tbody></table>';
  itensDiv.innerHTML = html;
}

function renderResumo(sumario){
  if(!sumario){ resumoDiv.innerHTML = '<em>Sem sumário.</em>'; return; }
  const checks = sumario.checks || {};
  const diff = checks.difference_norm;
  let diffClass = 'diff-ok';
  if(diff === null || diff === undefined) diffClass = 'diff-ok';
  else if(Math.abs(diff) <= (checks.invoice_total_declared_norm? checks.invoice_total_declared_norm*0.01 : 0)) diffClass='diff-ok';
  else if(Math.abs(diff) <= (checks.invoice_total_declared_norm? checks.invoice_total_declared_norm*0.05 : 0)) diffClass='diff-warn';
  else diffClass='diff-bad';
  resumoDiv.innerHTML = `
    <div><strong>Status:</strong> ${esc(sumario.status||'')} <span class='tooltip'>ℹ<span class='tip'>${esc(TOOLTIP_STATUS)}</span></span></div>
    <div class="checks">
      <span>Itens Somados: ${checks.total_items_sum_norm ?? '-'}</span>
      <span>Total Declarado: ${checks.invoice_total_declared_norm ?? '-'}</span>
      <span>Diferença: ${checks.difference_norm ?? '-'}</span>
    </div>
    <div class="diff-box ${diffClass}">Diferença Avaliação: ${diff===null||diff===undefined?'-':diff}</div>
    <div style="margin-top:4px; font-size:.7rem;">Erros críticos: ${sumario.total_erros_criticos ?? 0} | Alertas: ${sumario.total_alertas ?? 0} | Observações: ${sumario.total_observacoes ?? 0}</div>
    <div style="margin-top:4px; font-size:.7rem;">${esc(sumario.conclusao || '')}</div>
    ${(sumario.alertas&&sumario.alertas.length)?`<div style='margin-top:6px; font-size:.6rem; color:#b45309;'><strong>Alertas:</strong> ${sumario.alertas.map(esc).join(' | ')}</div>`:''}
  `;
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  statusDiv.textContent = 'Enviando...';
  previewDiv.textContent = '';
  jsonDiv.textContent = '';
  painelEstruturado.style.display = 'none';
  const btn = form.querySelector('button');
  btn.disabled = true;
  try {
    const fd = new FormData(form);
    const resp = await fetch('/conferencia/simple/analyze', { method: 'POST', body: fd });
    const data = await resp.json();
    if(!data.success){
      statusDiv.innerHTML = `<span class='status-err'>Erro: ${data.error||'desconhecido'}</span>`;
    } else {
      statusDiv.innerHTML = `<span class='status-ok'>Processado em ${data.elapsed_ms} ms (Lexoid: ${data.lexoid_mode})</span>`;
      previewDiv.textContent = 'Markdown preview (1.2k chars)\n\n' + (data.markdown_preview || '');
      const jsonData = data.json || { aviso: 'Sem JSON retornado', llm_error: data.llm_error };
      jsonDiv.textContent = JSON.stringify(jsonData, null, 2);
      // Render estruturado
      renderResumo(jsonData.sumario);
      renderCampos(jsonData.campos || {});
      renderItens(jsonData.itens_da_fatura || []);
      painelEstruturado.style.display = 'block';
    }
  } catch(err){
    statusDiv.innerHTML = `<span class='status-err'>Falha inesperada: ${err}</span>`;
  } finally {
    btn.disabled = false;
  }
});
