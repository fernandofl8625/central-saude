#!/bin/bash

# Garante que o script rode na pasta onde o arquivo está localizado
cd "$(dirname "$0")"

echo "==================================================="
echo "   INSTALADOR AUTOMATICO - CENTRAL SAUDE (macOS)   "
echo "==================================================="
echo ""

# 1. Verificar se o requirements.txt existe
if [ ! -f "requirements.txt" ]; then
    echo "[ERRO] O arquivo 'requirements.txt' nao foi encontrado nesta pasta!"
    echo "[!] Certifique-se de extrair todos os arquivos do .zip juntos."
    read -p "Pressione ENTER para sair..."
    exit 1
fi

# 2. Verificar e Instalar Python 3 Automaticamente no macOS
if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 nao encontrado no Mac. Baixando e instalando automaticamente..."
    curl -L https://www.python.org/ftp/python/3.11.9/python-3.11.9-macos11.pkg -o python_setup.pkg
    
    echo "[i] Instalando o Python (pode solicitar sua senha do Mac para autorizar a instalacao)..."
    sudo installer -pkg python_setup.pkg -target /
    rm -f python_setup.pkg
    echo "[OK] Python 3 instalado com sucesso!"
else
    echo "[OK] Python 3 ja esta instalado no seu Mac."
fi

# 3. Verificar e Instalar Ollama no macOS
if ! command -v ollama &> /dev/null; then
    echo ""
    echo "[!] Ollama nao encontrado. Baixando motor de IA para macOS..."
    curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama.zip
    unzip -q Ollama.zip
    if [ -d "/Applications" ]; then
        mv Ollama.app /Applications/
        echo "[OK] Ollama instalado na pasta Aplicativos!"
    fi
    rm -f Ollama.zip
else
    echo ""
    echo "[OK] Ollama ja esta instalado no macOS."
fi

# 4. Inicializar o servico e baixar o modelo de IA
echo ""
echo "[+] Inicializando motor de IA local..."
open -a Ollama 2>/dev/null || true
sleep 3
ollama pull llama3 &

# 5. Configurar Ambiente Virtual do Python e Dependencias
echo ""
echo "[+] Criando ambiente Python isolado (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

echo "[+] Instalando dependencias do sistema..."
venv/bin/python3 -m pip install --upgrade pip > /dev/null 2>&1
venv/bin/python3 -m pip install -r requirements.txt

echo ""
echo "==================================================="
echo "  INSTALACAO CONCLUIDA COM SUCESSO!                "
echo "  Use o arquivo 'iniciar_central.command' para abrir. "
echo "==================================================="
read -p "Pressione ENTER para finalizar..."