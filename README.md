# UniSystem Portal - Unique Aduaneira

Portal web corporativo para a Unique Aduaneira, desenvolvido com Flask e Supabase.

## Módulos Disponíveis

1. **Dashboard** - Visão geral das operações e métricas principais
2. **One Page** - Interface simplificada para clientes e usuários internos
3. **Conferência Documental IA** - Verificação automatizada de documentos com OCR e IA
4. **Agente Unique** - Agente conversacional para atendimento ao cliente
5. **Relatórios** - Geração e visualização de relatórios personalizados
6. **Usuários** - Gerenciamento de usuários e permissões (apenas admin)

## Requisitos de Sistema

- Python 3.8 ou superior
- Flask e dependências (ver requirements.txt)
- Supabase (para banco de dados e autenticação)
- Para o módulo de Conferência Documental IA:
  - Poppler (para o pdf2image)
  - Chave de API para Google Gemini

## Instalação

1. Clone o repositório:
```bash
git clone [URL_DO_REPOSITORIO]
cd portal-unique
```

2. Crie um ambiente virtual Python:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
```
SUPABASE_URL=sua_url_do_supabase
SUPABASE_KEY=sua_chave_do_supabase
SECRET_KEY=sua_chave_secreta_flask
FLASK_DEBUG=True
```

5. Configure o banco de dados Supabase:
- Execute os scripts SQL na pasta `sql/` para criar as tabelas:
  - users (usuários do sistema)
  - conferencia_jobs (para o módulo de Conferência Documental IA)
  - outras tabelas conforme necessário
- Configure as políticas de Row Level Security (RLS) para cada tabela

6. Para o módulo de Conferência Documental IA, configure a API do Gemini:
   - Adicione sua chave de API ao arquivo `.env`: `GEMINI_API_KEY=sua-chave-gemini-aqui`

7. Execute a aplicação:
```bash
python app.py
```

Ou use o script de inicialização:
```bash
./start.bat   # Windows
```

A aplicação estará disponível em `http://localhost:5000`

## Módulo de Conferência Documental IA

O módulo de Conferência Documental IA permite verificar automaticamente documentos aduaneiros como invoices, packlists e conhecimentos de embarque.

### Funcionalidades:

- Extração inteligente de texto de documentos PDF
- Análise baseada em IA (Google Gemini)
- Verificação de conformidade com o Art. 557 do regulamento aduaneiro
- Classificação de problemas em 3 níveis (erro crítico, alerta, observação)
- Interface amigável para upload e visualização de resultados

Para mais detalhes, consulte a [documentação completa](docs/conferencia_documental.md) e o [guia de instalação](docs/conferencia_instalacao.md).

## Níveis de Acesso

- **admin**: Acesso completo a todos os módulos
- **interno_unique**: Acesso aos módulos internos, incluindo Conferência Documental IA
- **cliente_unique**: Acesso limitado (One Page e Agente Unique)

## Estrutura do Projeto

```
app/
├─ main.py
├─ config.py
├─ routes/
│ ├─ auth.py
│ ├─ dashboard.py
│ ├─ relatorios.py
│ └─ usuarios.py
├─ templates/
├─ static/
└─ requirements.txt
```

## Funcionalidades

- Autenticação de usuários via Supabase Auth
- Dashboard com gráficos interativos
- Geração de relatórios em PDF
- Gestão de usuários
- Controle de acesso baseado em perfis

## Perfis de Usuário

- **interno_unique**: Funcionários com acesso completo
- **externo_clientes**: Clientes com acesso restrito
- **admin**: Administradores com acesso total

## Tecnologias Utilizadas

- Backend: Python 3.x + Flask
- Banco de Dados: Supabase (PostgreSQL)
- Frontend: Bootstrap 5
- Dashboards: Plotly
- Geração de PDF: WeasyPrint

## Contribuição

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes. 