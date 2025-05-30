@echo off
echo Iniciando o UniSystem Portal com o módulo de Conferência Documental IA...

REM Verifica se o Python está instalado
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Erro: Python não encontrado. Por favor, instale o Python.
    pause
    exit /b 1
)

REM Verifica se o arquivo .env existe
if not exist .env (
    echo Aviso: Arquivo .env não encontrado. Criando um arquivo .env de exemplo...
    copy .env.example .env
    echo Por favor, edite o arquivo .env com suas configurações antes de continuar.
    pause
    exit /b 1
)

REM Instala as dependências necessárias
echo Instalando dependências...
pip install -r requirements.txt

REM Cria o diretório de uploads se não existir
if not exist static\uploads\conferencia (
    echo Criando diretório para uploads...
    mkdir static\uploads\conferencia
)

REM Inicia a aplicação
echo Iniciando a aplicação...
python app.py

pause
