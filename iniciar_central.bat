@echo off
title Central Saude v1.0.0
color 0B

echo Iniciando a Central Saude...
call venv\Scripts\activate.bat
python -m streamlit run app.py --server.headless=false