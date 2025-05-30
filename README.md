# Portal UniSystem

Portal web corporativo para a UniSystem, desenvolvido com Flask e Supabase.

## Requisitos

- Python 3.x
- pip (gerenciador de pacotes Python)
- Conta no Supabase (para banco de dados e autenticação)

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
- Crie as tabelas necessárias no Supabase:
  - users (id, nome, email, role)
- Configure as políticas de Row Level Security (RLS) para cada tabela

6. Execute a aplicação:
```bash
flask run
```

A aplicação estará disponível em `http://localhost:5000`

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