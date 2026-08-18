@echo off
title Instalador Inteligente - Central Saude v1.0.0 (Windows)
color 0A

cd /d "%~dp0"

echo ===================================================
echo     INSTALADOR AUTOMATICO - CENTRAL SAUDE (WINDOWS)
echo ===================================================
echo.

:: 1. Verificar se o requirements.txt existe
if not exist "requirements.txt" (
    echo [ERRO] O arquivo 'requirements.txt' nao foi encontrado nesta pasta!
    echo [!] Certifique-se de extrair todos os arquivos do .zip juntos.
    echo.
    pause
    exit
)

:: 2. Verificar e Instalar Python Automaticamente
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python nao encontrado. Baixando e instalando o Python automaticamente...
    curl -L https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe -o python_setup.exe
    echo [i] Instalando o Python em segundo plano (aguarde cerca de 1 minuto)...
    start /wait python_setup.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    if exist python_setup.exe del python_setup.exe
    
    :: Atualiza o PATH da sessao atual do Prompt
    set "PATH=%SystemDrive%\Program Files\Python311;%SystemDrive%\Program Files\Python311\Scripts;%PATH%"
    echo [OK] Python instalado com sucesso!
) else (
    echo [OK] Python ja esta instalado na maquina.
)

:: 3. Verificar e Instalar Ollama se nao existir
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [!] Ollama nao detectado. Baixando e instalando motor de IA local...
    curl -L https://ollama.com/download/OllamaSetup.exe -o OllamaSetup.exe
    echo [i] Executando instalador do Ollama...
    start /wait OllamaSetup.exe /silent
    if exist OllamaSetup.exe del OllamaSetup.exe
    echo [OK] Motor de IA instalado com sucesso!
) else (
    echo.
    echo [OK] Ollama ja esta instalado na maquina.
)

:: 4. Baixar o modelo Llama em segundo plano
echo.
echo [+] Garantindo que o modelo de IA local esteja pronto...
start /b ollama pull llama3 >nul 2>&1

:: 5. Configurar Ambiente Virtual e Instalar Dependencias
echo.
echo [+] Configurando ambiente Python isolado (venv)...
if not exist "venv" (
    python -m venv venv
)

echo [+] Instalando dependencias do sistema...
venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo ===================================================
echo  INSTALACAO CONCLUIDA COM SUCESSO!
echo  Para abrir a Central Saude, use o 'iniciar_central.bat'.
echo ===================================================