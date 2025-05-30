# Guia de Instalação - Conferência Documental IA

Este guia detalha os passos para instalação e configuração do módulo de Conferência Documental IA no sistema UniSystem Portal.

## 1. Pré-requisitos

### 1.1 Poppler (para pdf2image)

O módulo utiliza Poppler para converter PDFs em imagens, necessário para processamento com Gemini AI.

#### Windows
1. Baixe o binário do [Poppler para Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extraia em uma pasta de sua preferência (por exemplo, `C:\Program Files\poppler`)
3. Adicione o caminho à variável de ambiente PATH

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install -y poppler-utils
```

#### macOS
```bash
brew install poppler
```

## 2. Dependências Python

### 2.1 Instalar pacotes Python necessários

```bash
pip install PyPDF2 pdf2image pillow google-generativeai tqdm aiohttp
```

## 3. Configuração do Banco de Dados

Execute o script SQL para criar a tabela `conferencia_jobs` no Supabase:

1. Acesse o dashboard do Supabase: https://app.supabase.io
2. Navegue até a seção SQL
3. Execute o script contido no arquivo `sql/v3_conferencia_jobs.sql`

## 4. Configuração de Ambiente

### 4.1 Criar arquivo .env

Crie ou edite o arquivo `.env` na raiz do projeto e adicione as seguintes variáveis:

```
# Chave de API para Gemini
GEMINI_API_KEY=sua-chave-gemini-aqui
```

### 4.2 Criar diretório para uploads

```bash
# No Windows
mkdir -p "static\uploads\conferencia"

# No Linux/macOS
mkdir -p static/uploads/conferencia
```

Certifique-se de que o diretório tem permissões de escrita para o usuário que executa a aplicação.

## 5. Verificação da Instalação

Para verificar se a instalação foi bem-sucedida, execute os seguintes comandos:

### 5.1 Verificar Poppler
```bash
# Windows
pdftoppm -v

# Linux/macOS
pdftoppm -v
```

### 5.2 Verificar pdf2image
```python
python -c "import pdf2image; print('pdf2image importado com sucesso')"
```

### 5.3 Verificar Gemini API
```python
python -c "import google.generativeai as genai; print('Gemini API importada com sucesso')"
```

## 6. Solução de Problemas Comuns

### 6.1 Tesseract não encontrado
Se você receber um erro indicando que o Tesseract não foi encontrado, defina explicitamente o caminho no arquivo `.env`:
```
TESSERACT_CMD=C:\caminho\completo\para\tesseract.exe
```

### 6.2 Poppler não encontrado
Se você receber um erro relacionado ao Poppler, certifique-se de que o programa está no PATH ou defina o caminho diretamente no código:

```python
# Adicione isso antes de usar pdf2image
os.environ['PATH'] += os.pathsep + r'C:\Program Files\poppler\bin'
```

### 6.3 Erros de OCR
Se o OCR não estiver produzindo resultados satisfatórios:
- Verifique se o pacote de idioma português está instalado
- Tente pré-processar os PDFs para melhorar a qualidade (aumentar contraste, remover ruído)
- Ajuste os parâmetros de OCR no código para melhorar o reconhecimento

### 6.4 Erros de API
Se ocorrerem erros ao chamar as APIs de IA:
- Verifique se as chaves de API estão corretas no arquivo `.env`
- Verifique se você tem créditos suficientes nas respectivas plataformas
- Verifique sua conexão com a internet

## 7. Suporte e Contato

Caso encontre problemas durante a instalação ou uso do módulo, entre em contato com a equipe de desenvolvimento:
- Email: [suporte@uniqueaduaneira.com.br]
- Telefone: [INSERIR NÚMERO]

---

Última atualização: 29 de maio de 2025
