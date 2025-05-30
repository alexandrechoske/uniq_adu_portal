# Conferência Documental IA

Este módulo permite a verificação automatizada de documentos aduaneiros utilizando OCR (Reconhecimento Óptico de Caracteres) e Inteligência Artificial.

## Funcionalidades

- Processamento inteligente de PDFs para extração de texto
- Análise documental com IA (Google Gemini)
- Verificação de conformidade de documentos aduaneiros
- Geração de relatórios detalhados
- Anotação de PDFs com os resultados da análise

## Requisitos

Para utilizar este módulo, você precisa:

1. Python 3.8+ instalado
2. Dependências Python listadas em requirements.txt
3. Chave de API para o Google Gemini (obrigatório)

## Instalação

### 1. Instalar dependências Python
```bash
pip install -r requirements.txt
```

### 2. Configurar a chave de API do Gemini

Crie ou edite o arquivo `.env` na raiz do projeto e adicione sua chave:

```
GEMINI_API_KEY=sua-chave-gemini-aqui
```

Se você não fornecer chaves de API, o sistema utilizará resultados de exemplo para simulação.

## Fluxo de Trabalho

1. O usuário acessa a página principal do módulo
2. Seleciona o tipo de conferência (Invoice, Packlist, Conhecimento ou Geral)
3. Faz upload dos documentos PDF para análise
4. O sistema processa os documentos com Gemini AI para extrair e analisar o texto
5. Os resultados são exibidos com indicadores de status coloridos
6. O usuário pode ver detalhes da análise ou baixar um PDF anotado

## Tipos de Conferência

- **Conferência de Inconsistências**: Verificação geral de inconsistências em todos os tipos de documentos
- **Conferência de Invoices**: Verificação específica para invoices comerciais
- **Conferência de Packlists**: Verificação específica para packlists
- **Conferência de Conhecimentos**: Verificação específica para conhecimentos de embarque (BL/AWB)

## Estrutura de Códigos

```
routes/
  ├── conferencia.py          # Blueprint principal e lógica de processamento
  └── conferencia_pdf.py      # Blueprint para anotação de PDFs
static/
  └── uploads/
      └── conferencia/        # Diretório para armazenar uploads
templates/
  └── conferencia/
      └── index.html          # Template da interface do usuário
sql/
  └── v3_conferencia_jobs.sql # Script de criação da tabela no banco
```

## Níveis de Severidade

Os resultados da conferência são classificados em três níveis:

1. **ERRO CRÍTICO**: Informações obrigatórias ausentes ou incorretas
2. **ALERTA**: Informações que precisam de atenção ou verificação adicional
3. **OBSERVAÇÃO**: Pequenos enganos aceitáveis ou sugestões de melhoria

## Tecnologias Utilizadas

- **Backend**: Python/Flask
- **Processamento de PDF**: PyPDF2, pdf2image
- **IA**: Google Gemini AI
- **Frontend**: HTML, CSS, JavaScript (com TailwindCSS)
- **Banco de Dados**: Supabase

## Limitações Atuais

- Documentos com layouts muito complexos podem ser interpretados incorretamente
- O processamento pode ser lento dependendo do tamanho e quantidade de arquivos
- A qualidade da análise depende da capacidade do Gemini AI em entender o contexto documental
- Documentos de baixa qualidade ou excessivamente complexos podem exigir revisão manual

## Próximas Melhorias

- Implementação de filas de processamento com Celery para melhor escalabilidade
- Suporte para mais tipos de documentos aduaneiros
- Interface para ajustar os critérios de verificação
- Sistema de feedback para melhorar os modelos de IA
- Comparação lado a lado de documentos relacionados
