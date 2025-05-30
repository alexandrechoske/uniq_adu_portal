@echo off
echo Instalador do Tesseract OCR para o módulo de Conferência Documental IA
echo ================================================================
echo.
echo Este script irá baixar e instalar:
echo 1. Tesseract OCR 5.3.1 (64-bit)
echo 2. Pacote de idioma português para OCR
echo.
echo Requisitos: Conexão com a internet e permissões de administrador
echo.

set /p continuar="Deseja continuar com a instalação? (S/N): "
if /i "%continuar%" neq "S" goto :fim

echo.
echo Baixando o instalador do Tesseract OCR...
echo.

set TESSERACT_INSTALLER=tesseract-ocr-w64-setup-5.3.1.20230401.exe
set DOWNLOAD_URL=https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.1.20230401.exe

powershell -Command "Invoke-WebRequest -Uri '%DOWNLOAD_URL%' -OutFile '%TESSERACT_INSTALLER%'"

if not exist %TESSERACT_INSTALLER% (
    echo Erro ao baixar o instalador. Verifique sua conexão com a internet e tente novamente.
    goto :fim
)

echo.
echo Baixado com sucesso. Iniciando a instalação...
echo.
echo Por favor, durante a instalação:
echo - Selecione "Additional language data" para incluir o idioma português
echo - Marque a opção "Portuguese" na lista de idiomas
echo - Adicione o Tesseract ao PATH quando solicitado
echo.
echo Aguarde o instalador abrir...

start /wait %TESSERACT_INSTALLER% /SILENT

echo.
echo Instalação concluída. Verificando a instalação...
echo.

tesseract --version

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Aviso: O Tesseract OCR pode não ter sido adicionado ao PATH corretamente.
    echo Por favor, adicione manualmente o diretório de instalação do Tesseract ao PATH do sistema.
    echo Normalmente localizado em "C:\Program Files\Tesseract-OCR"
    echo.
    echo Após adicionar ao PATH, reinicie seu computador.
) else (
    echo.
    echo Tesseract OCR instalado com sucesso!
)

echo.
echo Configurando o caminho do Tesseract no arquivo .env...
echo.

echo TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe >> .env
echo.
echo Caminho do Tesseract adicionado ao arquivo .env

:fim
echo.
echo Fim do processo de instalação.
echo.
del %TESSERACT_INSTALLER%

pause
