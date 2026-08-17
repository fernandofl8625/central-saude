from datetime import datetime
import pandas as pd
import streamlit as st


def safe_int(val, default=0) -> int:
    """Converte valores com tratamento para NaN, None ou tipos incompatíveis."""
    if pd.isna(val) or val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def render_tab_dashboard(db, ai_assistant, correlation_engine, pdf_generator, metas_user):
    df = db.buscar_historico_telemetria()
    df_exames = db.buscar_historico_exames()

    if df.empty or "Passos" not in df.columns:
        st.info("Nenhum dado registrado para gerar a análise.")
        return

    u = df.iloc[0]

    # LEMBRETES CONTEXTUAIS
    hora_atual = datetime.now().hour
    cafe_hoje = safe_int(u.get('ConsumoCafeML'), 0)
    agua_hoje = safe_int(u.get('ConsumoAguaML'), 0)

    if hora_atual >= 14 and cafe_hoje > 0:
        st.warning("⚠️ **Janela de Cafeína Encerrada:** Recomendamos encerrar bebidas estimulantes após às 14:00 para não achatar o sono REM na noite de hoje.")

    if hora_atual >= 18 and agua_hoje < 1800:
        st.info(
            f"💧 **Aviso de Hidratação:** Você registrou `{agua_hoje} ml` de água hoje. Beba mais água no início da noite para atingir sua meta diária.")

    # MÉTRICAS PRINCIPAIS
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Passos", f"{safe_int(u.get('Passos'), 0):,}",
              f"{safe_int(u.get('MinutosAtivos'), 0)} min ativos")
    readiness_val = safe_int(u.get('ScoreProntitudade'), 75)
    m2.metric("Prontidão (Readiness)",
              f"{readiness_val} / 100", f"Sono: {u.get('HorasSono', 0) or 0}h")
    fc_val = safe_int(u.get('FrequenciaCardiacaRepouso'), 0)
    spo2_val = u.get('SpO2MedioPct', 96.5) or 96.5
    m3.metric("FC Repouso / SpO₂", f"{fc_val} BPM", f"SpO₂ {spo2_val}%")
    m4.metric("Bateria / Estresse", f"{safe_int(u.get('NivelEnergiaScore'), 0)}%",
              f"Estresse {safe_int(u.get('NivelEstresseScore'), 0)}")

    st.markdown("---")

    # PAINEL DE CONQUISTAS & STREAKS
    stats_milestones = db.calcular_milestones_e_streaks()

    st.markdown("#### 🏆 Conquistas & Sequências de Hábitos (Streaks)")
    c_st1, c_st2, c_st3, c_st4 = st.columns(4)
    c_st1.metric("🔥 Ofensiva de Água",
                 f"{stats_milestones.get('streak_agua_dias', 0)} dias", "Meta 2.500ml")
    c_st2.metric("😴 Ofensiva de Sono",
                 f"{stats_milestones.get('streak_sono_dias', 0)} dias", "Meta 7.0h+")
    c_st3.metric("🚶‍♂️ Ofensiva de Atividade",
                 f"{stats_milestones.get('streak_treino_dias', 0)} dias", "5.000+ passos")
    c_st4.metric("🦶 Total Acumulado",
                 f"{stats_milestones.get('total_passos_acumulados', 0):,}", "passos salvos")

    if stats_milestones.get("badges"):
        badge_cols = st.columns(len(stats_milestones["badges"]))
        for idx, bg in enumerate(stats_milestones["badges"]):
            badge_cols[idx].success(f"**{bg['titulo']}**\n\n*{bg['desc']}*")

    st.markdown("---")

    # ALERTAS DE FADIGA DO SNC
    alertas_snc = correlation_engine.detectar_alertas_fadiga_snc(df)
    if alertas_snc:
        st.markdown("#### 🚨 Central de Monitoramento de Fadiga & SNC")
        for al in alertas_snc:
            if al['nivel'] == 'danger':
                st.error(f"**{al['titulo']}**\n\n{al['msg']}")
            elif al['nivel'] == 'warning':
                st.warning(f"**{al['titulo']}**\n\n{al['msg']}")
        st.markdown("---")

    # --- CENTRAIS GRÁFICAS DE VISUALIZAÇÃO ---
    st.markdown("### 📊 Telemetria Pessoal em Gráficos")

    df_graficos = df.sort_values(by="DataRegistro").set_index("DataRegistro")

    g_col1, g_col2 = st.columns(2)

    with g_col1:
        st.markdown("##### 📈 1. Prontidão (Readiness) & Bateria Corporal")
        cols_r = [c for c in ["ScoreProntitudade", "QualidadeSonoScore",
                              "NivelEnergiaScore"] if c in df_graficos.columns]
        if cols_r:
            st.line_chart(df_graficos[cols_r])

    with g_col2:
        st.markdown("##### 💧 2. Balanço Hídrico x Cafeína (mL)")
        cols_bebidas = [c for c in ["ConsumoAguaML",
                                    "ConsumoCafeML"] if c in df_graficos.columns]
        if cols_bebidas:
            st.bar_chart(df_graficos[cols_bebidas])

    g_col3, g_col4 = st.columns(2)

    with g_col3:
        st.markdown("##### 🚶‍♂️ 3. Volume Diário de Passos")
        if "Passos" in df_graficos.columns:
            st.bar_chart(df_graficos["Passos"])

    with g_col4:
        st.markdown("##### 😴 4. Estágios do Sono (Watch 4 - min)")
        cols_sono = [c for c in ["SonoProfundoMinutos",
                                 "SonoREMMinutos"] if c in df_graficos.columns]
        if cols_sono:
            st.area_chart(df_graficos[cols_sono])

    st.markdown("---")

    # ASSISTENTE VIRTUAL DE SAÚDE
    st.markdown("### 🤖 Assistente Virtual de Saúde & Fisiologia")
    st.caption("Consulte o diagnóstico automatizado combinando métricas do Watch 4 e o protocolo de suplementos/medicamentos.")

    if "parecer_ia_atual" not in st.session_state:
        st.session_state.parecer_ia_atual = ""

    if st.button("✨ Gerar Parecer Diagnóstico Personalizado", type="primary"):
        with st.spinner("Analisando fisiologia do sono do Watch 4, SpO₂, FC noturna e medicamentos..."):
            try:
                st.session_state.parecer_ia_atual = ai_assistant.gerar_parecer()
            except Exception as e_ia:
                st.session_state.parecer_ia_atual = f"⚠️ Ocorreu um erro ao consultar o assistente: {e_ia}"
            st.rerun()

    if st.session_state.parecer_ia_atual:
        st.markdown(st.session_state.parecer_ia_atual)

    st.markdown("---")

    # CHAT CONVERSACIONAL COM A TELEMETRIA
    st.markdown("### 💬 Chat Conversacional com sua Telemetria")
    st.caption(
        "Faça perguntas diretas à IA sobre seu histórico de sono, exames, medicação e hábitos:")

    if "historico_chat" not in st.session_state:
        st.session_state.historico_chat = []

    c_a1, c_a2, c_a3, c_a4 = st.columns(4)
    pergunta_clicada = None
    if c_a1.button("🔋 Sono Profundo x Disposição", width="stretch"):
        pergunta_clicada = "Qual a relação do meu sono profundo recente com a minha disposição matinal?"
    if c_a2.button("☕ Impacto do Café na FC", width="stretch"):
        pergunta_clicada = "Como o meu consumo de café está afetando minha frequência cardíaca de repouso?"
    if c_a3.button("💊 Análise do Protocolo", width="stretch"):
        pergunta_clicada = "Qual a avaliação do meu protocolo atual de medicamentos e suplementos?"
    if c_a4.button("🩸 Exames em Destaque", width="stretch"):
        pergunta_clicada = "Quais marcadores laboratoriais recentes precisam de mais atenção?"

    pergunta_input = st.chat_input(
        "Digite sua pergunta sobre seu histórico de saúde...")
    pergunta_final = pergunta_clicada or pergunta_input

    if pergunta_final:
        st.session_state.historico_chat.append(
            {"role": "user", "content": pergunta_final})
        with st.spinner("Consultando dados da telemetria no banco..."):
            resp = ai_assistant.responder_chat_telemetria(pergunta_final)
            st.session_state.historico_chat.append(
                {"role": "assistant", "content": resp})

    for msg in st.session_state.historico_chat:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

    st.markdown("---")

    # GERADOR DE PDF
    c_btn1, c_btn2 = st.columns([3, 1])
    c_btn1.markdown("### 📄 Relatório de Saúde Integrado")

    try:
        pdf_bytes = pdf_generator.gerar_pdf_saude_completo(
            df, df_exames, parecer_ia=st.session_state.parecer_ia_atual, metas_user=metas_user
        )
        if pdf_bytes:
            nome_pdf = f"relatorio_saude_{datetime.now().strftime('%Y%m%d')}.pdf"
            c_btn2.download_button(
                label="📥 Baixar PDF Atualizado",
                data=pdf_bytes,
                file_name=nome_pdf,
                mime="application/pdf",
                width="stretch"
            )
    except Exception as e_pdf:
        st.error(f"Erro ao gerar o arquivo PDF: {e_pdf}")

    df_7 = df.head(7)
    med_passos = safe_int(df_7['Passos'].fillna(0).mean())
    med_sono = round(float(df_7['HorasSono'].fillna(0).mean()), 1)
    med_score_sono = safe_int(df_7['QualidadeSonoScore'].fillna(0).mean())
    med_agua = safe_int(df_7['ConsumoAguaML'].fillna(0).mean())
    med_cafe = safe_int(df_7['ConsumoCafeML'].fillna(0).mean())
    med_cafeina = safe_int(df_7['ConsumoCafeinaMG'].fillna(0).mean())
    med_fc = safe_int(df_7['FrequenciaCardiacaRepouso'].fillna(0).mean())
    med_estresse = safe_int(df_7['NivelEstresseScore'].fillna(0).mean())
    peso_ult = float(df['PesoKG'].dropna().iloc[0]
                     ) if not df['PesoKG'].dropna().empty else 92.0

    meta_agua_ideal = int(peso_ult * 35) if metas_user.get('meta_agua_auto',
                                                           1) else metas_user.get('meta_agua_fixa_ml', 2500)

    st.caption(
        f"Emissão: {datetime.now().strftime('%d/%m/%Y às %H:%M')} | Amostragem: Últimos 30 dias de telemetria")

    # TABELA DE RESUMO EXECUTIVO
    st.markdown(
        "#### 1. Resumo Executivo vs. Metas Personalizadas (Média 7 dias)")
    dados_resumo = {
        "Métrica": ["Passos Diários", "Horas de Sono", "Score de Sono", "Hidratação Total", "Estimulantes (ml)", "Cafeína Estimada", "FC em Repouso", "Estresse"],
        "Média Registrada": [f"{med_passos:,} passos", f"{med_sono}h / noite", f"{med_score_sono} / 100", f"{med_agua} ml", f"{med_cafe} ml", f"{med_cafeina} mg", f"{med_fc} BPM", f"{med_estresse} / 100"],
        "Meta Personalizada": [f"{metas_user.get('meta_passos', 8000):,} passos", f"{metas_user.get('meta_sono_horas', 7.0)}h / noite", f">{metas_user.get('meta_score_sono', 75)}/100", f"{meta_agua_ideal} ml", f"<= {metas_user.get('limite_cafe_ml', 300)} ml", "< 300 mg", "60 - 80 BPM", "< 40/100"],
        "Status Geral": [
            "✅ Adequado" if med_passos >= metas_user.get(
                'meta_passos', 8000) else "⚠️ Abaixo da Meta",
            "✅ Adequado" if med_sono >= metas_user.get(
                'meta_sono_horas', 7.0) else "🔴 Privação de Sono",
            "✅ Bom" if med_score_sono >= metas_user.get(
                'meta_score_sono', 75) else "🟡 Regular",
            "✅ Ideal" if med_agua >= meta_agua_ideal else "⚠️ Abaixo do Recomendado",
            "✅ Moderado" if med_cafe <= metas_user.get(
                'limite_cafe_ml', 300) else "⚠️ Elevado",
            "✅ Controlado" if med_cafeina <= 300 else "🔴 Elevado",
            "✅ Normal" if 60 <= med_fc <= 80 else "🟡 Fora da Faixa",
            "✅ Baixo" if med_estresse < 40 else "⚠️ Moderado/Alto"
        ]
    }
    st.table(pd.DataFrame(dados_resumo))

    # MATRIZ DE CORRELAÇÃO DE PEARSON
    st.markdown("#### 🧠 2. Matriz de Correlação & Padrões Comportamentais")
    insights_corr = correlation_engine.gerar_insights_correlacao(df)
    for insight in insights_corr:
        st.info(insight)

    matriz_df = correlation_engine.calcular_matriz_correlacao(df)
    if not matriz_df.empty:
        with st.expander("📊 Ver Tabela Completa do Coeficiente de Correlação de Pearson & Como Interpretar"):
            st.markdown("""
            > ℹ️ **Como interpretar a Matriz de Pearson (Valores de -1.0 a +1.0):**
            > * **Valores Positivos Próximos de +1.0 (Verde):** Indicam **Correlação Direta Forte**.
            > * **Valores Negativos Próximos de -1.0 (Vermelho):** Indicam **Correlação Inversa Forte**.
            > * **Valores Próximos de 0.0:** Indicam **Ausência de Correlação Direta**.
            """)
            st.dataframe(matriz_df, width="stretch")
