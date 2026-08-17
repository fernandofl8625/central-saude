@echo off
cd /d "%~dp0"

:: Se houver ambiente virtual venv na pasta do projeto, ativa ele
if exist "venv\Scripts\activate.bat" call venv\Scripts\activate.bat
if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat

:: Encerra instâncias soltas do Python no Streamlit
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Streamlit*" >nul 2>&1

:: Inicia o Streamlit
start /B python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8501

:: Aguarda o servidor carregar
timeout /t 4 /nobreak >nul

:: Abre o navegador
start "" "http://localhost:8501"