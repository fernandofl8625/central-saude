@echo off
title Instalador Inteligente - Central Saude v1.0.0 (Windows)
color 0A

echo ===================================================
echo     INSTALADOR AUTOMATICO - CENTRAL SAUDE (WINDOWS)
echo ===================================================
echo.

:: 1. Verificar se o Python esta instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python nao foi encontrado no Windows.
    echo [i] Baixe o Python em https://www.python.org/downloads/ e marque 'Add Python to PATH' na instalacao.
    pause
    exit
)

:: 2. Verificar e Instalar Ollama se nao existir
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ollama nao detectado. Baixando e instalando motor de IA local...
    curl -L https://ollama.com/download/OllamaSetup.exe -o OllamaSetup.exe
    echo [i] Executando instalador do Ollama...
    start /wait OllamaSetup.exe /silent
    if exist OllamaSetup.exe del OllamaSetup.exe
    echo [OK] Motor de IA instalado com sucesso!
) else (
    echo [OK] Ollama ja esta instalado na maquina.
)

:: 3. Baixar o modelo Llama em segundo plano
echo.
echo [+] Baixando o modelo de IA local (Llama)...
start /b ollama pull llama3 >nul 2>&1

:: 4. Configurar Ambiente Virtual e Dependencias
echo.
echo [+] Configurando ambiente Python isolado...
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat
echo [+] Instalando bibliotecas do sistema (requirements.txt)...
pip install -r requirements.txt >nul 2>&1

echo.
echo ===================================================
echo  INSTALACAO CONCLUIDA COM SUCESSO!
echo  Para abrir a Central Saude no dia a dia, use o 'iniciar_central.bat'.
echo ===================================================
pause