@echo off
title Central Saude v1.0.0
echo Iniciando a Central Saude...
python -m streamlit run app.py --server.headless=false
pause