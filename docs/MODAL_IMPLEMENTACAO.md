# Modal de Detalhes do Processo - Implementação Compartilhada

## 📋 **Visão Geral**

Sistema de modal reutilizável implementado para exibir detalhes completos de processos de importação. O modal está disponível em:
- ✅ **Dashboard Executivo** (`/dashboard-executivo/`)
- ✅ **Dashboard de Materiais** (`/dashboard-materiais/`)

## 🏗️ **Arquitetura**

### **Arquivos Compartilhados:**
```
/templates/shared/process_modal.html       # Template HTML do modal
/static/shared/process_modal.css          # Estilos CSS do modal  
/static/shared/process_modal.js           # Lógica JavaScript do modal
```

### **Vantagens da Abordagem:**
- ✅ **Manutenção Centralizada:** Alterações em um único lugar
- ✅ **Consistência:** Interface idêntica em todas as páginas
- ✅ **Reutilização:** Fácil implementação em novas páginas
- ✅ **Performance:** CSS e JS compartilhados

## 🎯 **Funcionalidades**

### **Timeline do Processo:**
- 5 etapas visuais: Abertura → Embarque → Chegada → Desembaraço → Finalizado
- Status automático baseado no campo `status_macro`
- Animação de pulso para etapa ativa
- Ícones MDI responsivos

### **Informações Exibidas:**
1. **Informações Gerais:** Ref. Unique, Importador, CNPJ, Status, etc.
2. **Carga e Transporte:** Modal, Container, Datas, Transit Time, Peso
3. **Aduaneiras:** DI, Canal, URFs, Datas de registro/desembaraço
4. **Financeiro:** Valores CIF, Frete, Armazenagem, Honorários, Total
5. **Documentos:** Placeholder para funcionalidade futura

### **Formatação Automática:**
- ✅ **CNPJ:** `11568948000164` → `11.568.948/0001-64`
- ✅ **Moeda:** `1624.66` → `R$ 1.624,66`
- ✅ **Números:** `320000` → `320.000`
- ✅ **Status Macro:** `"5 - AG REGISTRO"` → Step 5 ativo

## 🔧 **Como Implementar em Nova Página**

### **1. Incluir CSS e JS:**
```html
{% block extra_css %}
<link rel="stylesheet" href="{{ url_for('static', filename='shared/process_modal.css') }}">
{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='shared/process_modal.js') }}"></script>
{% endblock %}
```

### **2. Incluir Template:**
```html
<!-- Modal de Detalhes do Processo -->
{% include 'shared/process_modal.html' %}
```

### **3. Adicionar Coluna de Ações na Tabela:**
```html
<thead>
    <tr>
        <th>Ações</th>
        <!-- outras colunas -->
    </tr>
</thead>
```

### **4. Atualizar JavaScript da Tabela:**
```javascript
function updateTable(data) {
    // Armazenar dados globalmente
    window.currentOperations = data;
    
    data.forEach((item, index) => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <button class="action-btn" onclick="openProcessModal(${index})">
                    <i class="mdi mdi-eye"></i>
                </button>
            </td>
            <!-- outras células -->
        `;
    });
}
```

## 📱 **Responsividade**

### **Desktop:**
- Modal centralizado com largura máxima de 1000px
- Timeline horizontal com linha conectora
- Cards em grid 2/3 colunas

### **Mobile:**
- Modal em tela cheia com margens mínimas
- Timeline empilhada verticalmente
- Cards em coluna única
- Ícones e fontes reduzidos

## 🎨 **Customização**

### **Cores Principais:**
- **Primária:** `#007bff` (azul)
- **Sucesso:** `#28a745` (verde)
- **Neutro:** `#6c757d` (cinza)
- **Fundo:** `#f8f9fa` (cinza claro)

### **Ícones MDI Utilizados:**
- `mdi-file-document-outline` (Abertura)
- `mdi-truck` (Embarque)
- `mdi-airplane-landing` (Chegada)
- `mdi-check-circle-outline` (Desembaraço)
- `mdi-flag-checkered` (Finalizado)
- `mdi-close` (Fechar modal)
- `mdi-eye` (Ver detalhes)

## 🐛 **Debug e Logs**

O sistema inclui logs detalhados no console do navegador:
```javascript
[PROCESS_MODAL] Abrindo modal para processo: 11
[MODAL_DEBUG] ref_importador: AZ8584/25/MP
[MODAL_DEBUG] Status macro extraído: 5
[TIMELINE_DEBUG] Step 5 marcado como active
```

## 🚀 **Próximas Implementações**

- [ ] Sistema de documentos anexados
- [ ] Modal em outras páginas (Conferência, Relatórios, etc.)
- [ ] Edição inline de campos
- [ ] Exportação de dados do processo
- [ ] Histórico de alterações

---

**Autor:** GitHub Copilot  
**Data:** 21/07/2025  
**Versão:** 1.0
