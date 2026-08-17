#!/bin/bash

cd "$(dirname "$0")"

echo "==================================================="
echo "   INSTALADOR AUTOMATICO - CENTRAL SAUDE (macOS)   "
echo "==================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[!] Python 3 nao foi encontrado no seu Mac."
    echo "[i] Instale o Python 3 via https://www.python.org/downloads/ ou via Homebrew."
    read -p "Pressione ENTER para sair..."
    exit 1
fi

if ! command -v ollama &> /dev/null; then
    echo "[!] Ollama nao encontrado. Baixando motor de IA para macOS..."
    curl -L https://ollama.com/download/Ollama-darwin.zip -o Ollama.zip
    unzip -q Ollama.zip
    if [ -d "/Applications" ]; then
        mv Ollama.app /Applications/
        echo "[OK] Ollama instalado na pasta Aplicativos!"
    fi
    rm -f Ollama.zip
else
    echo "[OK] Ollama ja esta instalado no macOS."
fi

echo ""
echo "[+] Inicializando motor de IA..."
open -a Ollama 2>/dev/null || true
sleep 3
ollama pull llama3 &

echo ""
echo "[+] Criando ambiente Python isolado (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
echo "[+] Instalando dependencias do sistema..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1

echo ""
echo "==================================================="
echo "  INSTALACAO CONCLUIDA COM SUCESSO!                "
echo "  Use o arquivo 'iniciar_central.command' para abrir. "
echo "==================================================="
read -p "Pressione ENTER para finalizar..."