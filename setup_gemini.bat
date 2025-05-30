@echo off
echo Configuração da API Gemini para o módulo de Conferência Documental IA
echo ================================================================
echo.
echo Este script irá configurar a chave de API do Google Gemini para
echo o módulo de Conferência Documental IA.
echo.

set /p GEMINI_API_KEY="Digite sua chave da API Gemini: "

echo.
echo Verificando se o arquivo .env existe...

if exist .env (
    echo O arquivo .env existe. Verificando se já contém configuração para Gemini...
    
    findstr /C:"GEMINI_API_KEY" .env >nul
    if %ERRORLEVEL% EQU 0 (
        echo A chave GEMINI_API_KEY já existe no arquivo .env.
        set /p atualizar="Deseja atualizar a chave existente? (S/N): "
        
        if /i "%atualizar%" equ "S" (
            echo Atualizando a chave GEMINI_API_KEY no arquivo .env...
            powershell -Command "(Get-Content .env) -replace 'GEMINI_API_KEY=.*', 'GEMINI_API_KEY=%GEMINI_API_KEY%' | Set-Content .env"
            echo Chave atualizada com sucesso!
        ) else (
            echo Configuração mantida sem alterações.
        )
    ) else (
        echo Adicionando a chave GEMINI_API_KEY ao arquivo .env...
        echo GEMINI_API_KEY=%GEMINI_API_KEY% >> .env
        echo Chave adicionada com sucesso!
    )
) else (
    echo O arquivo .env não existe. Criando novo arquivo...
    echo GEMINI_API_KEY=%GEMINI_API_KEY% > .env
    echo Arquivo .env criado com sucesso!
)

echo.
echo ================================================================
echo Instalando dependências necessárias...
echo.

pip install google-generativeai==0.3.1

echo.
echo Verificando a instalação do pacote google-generativeai...
echo.

python -c "import google.generativeai as genai; print(f'Pacote do Gemini instalado com sucesso: {genai.__file__}')"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Erro ao verificar a instalação do pacote google-generativeai.
    echo Por favor, execute manualmente: pip install google-generativeai
) else (
    echo.
    echo Configuração concluída com sucesso!
    echo.
    echo Agora você pode iniciar o aplicativo com o comando: start.bat
)

echo.
pause
