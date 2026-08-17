from datetime import date
import streamlit as st


def render_tab_saude_mental(db, ai_assistant):
    data_reg = date.today()
    data_str = data_reg.strftime('%Y-%m-%d')

    st.subheader(
        f"🧠 Rastreio de Humor, Regulação Emocional & IA Terapeuta ({data_str})")
    st.caption(
        "Registre seu estado afetivo do dia e consulte a análise de acolhimento psicofisiológico:")

    reg_mental = db.buscar_registro_mental_data(data_str)

    # PARECER INICIAL / SESSÃO TERAPÊUTICA
    if st.button("💬 Iniciar Sessão de Acolhimento & Gerar Parecer Terapêutico (TCC)", type="primary"):
        with st.spinner("Analisando padrões cognitivos, gatilhos mentais e descompressão do dia..."):
            parecer_m = ai_assistant.gerar_parecer_terapeutico(data_str)
            st.session_state.parecer_terapeutico_hoje = parecer_m
            st.rerun()

    if "parecer_terapeutico_hoje" in st.session_state and st.session_state.parecer_terapeutico_hoje:
        st.markdown(st.session_state.parecer_terapeutico_hoje)
        st.markdown("---")

    # INTERFACE DO CHAT TERAPÊUTICO CONTÍNUO COM PERSISTÊNCIA EM BANCO DE DADOS
    st.markdown("### 💬 Conversa Contínua com a IA Terapeuta")
    st.caption("Converse sobre os gatilhos, desabafe ou aprofunde o reenquadramento TCC de hoje. Todas as mensagens são salvas no banco de dados:")

    historico_chat_db = db.buscar_historico_chat_terapeutico(data_str)

    # Exibe as mensagens já trocadas e salvas no banco
    for msg in historico_chat_db:
        if msg["origem"] == "usuario":
            st.chat_message("user").write(msg["mensagem"])
        else:
            st.chat_message("assistant").write(msg["mensagem"])

    msg_input = st.chat_input("Digite sua mensagem para a IA Terapeuta...")
    if msg_input:
        st.chat_message("user").write(msg_input)
        with st.spinner("IA Terapeuta refletindo sobre sua mensagem..."):
            resposta_terapeuta = ai_assistant.responder_chat_terapeutico(
                data_str, msg_input)
            st.chat_message("assistant").write(resposta_terapeuta)
        st.rerun()

    st.markdown("---")

    with st.form("form_saude_mental_diaria"):
        m1, m2 = st.columns(2)
        humor_sc = m1.slider("🎭 Escala do Estado de Humor (1 = Exausto, 10 = Excelente)", 1, 10, int(
            reg_mental.get('humor_score') or 6))

        opcoes_emocional = ["Tranquilo / Focado", "Entusiasmado / Motivado",
                            "Ansioso / Agitado", "Estressado / Pressionado", "Exaurido / Triste", "Neutro"]
        idx_emo = 0
        em_atual = reg_mental.get('estado_emocional', 'Tranquilo / Focado')
        if em_atual in opcoes_emocional:
            idx_emo = opcoes_emocional.index(em_atual)
        estado_emocional_sel = m2.selectbox(
            "Estado Predominante do Dia", opcoes_emocional, index=idx_emo)

        gatilhos_txt = st.text_input("⚡ Gatilhos Identificados no Dia (Opcional)", value=reg_mental.get(
            'gatilhos', ''), placeholder="Ex: Prazo de projeto, reunião, trânsito, café excessivo...")

        st.markdown("---")
        st.write(
            "🧘 **Descompressão Parassimpática & Hobbies (Oficina, Bonsai, Meditação, etc.):**")
        m3, m4 = st.columns(2)
        min_desc = m3.number_input("Tempo de Descompressão (minutos)", min_value=0, max_value=600, value=int(
            reg_mental.get('minutos_descompressao') or 0), step=5)
        ativ_desc = m4.text_input("Atividade Realizada", value=reg_mental.get(
            'atividade_descompressao', ''), placeholder="Ex: Marcenaria na oficina, Jardinagem/Bonsai, Leitura...")

        st.markdown("---")
        st.write(
            "📝 **Registro TCC (Terapia Cognitivo-Comportamental - Descarrego Mental):**")
        p_tcc = st.text_area("Pensamento Intrusivo / Preocupação do Dia (E se...?)", value=reg_mental.get(
            'diario_tcc_pensamento', ''), placeholder="Ex: Receio de não entregar a demanda no prazo...")
        r_tcc = st.text_area("Reenquadramento Racional (Fatos x Pensamentos)", value=reg_mental.get(
            'diario_tcc_reenquadramento', ''), placeholder="Ex: O projeto está adiantado e estruturei um plano claro...")

        if st.form_submit_button("💾 Salvar Registro de Saúde Mental"):
            dados_m = {
                "data_registro": data_str,
                "humor_score": humor_sc,
                "estado_emocional": estado_emocional_sel,
                "gatilhos": gatilhos_txt,
                "minutos_descompressao": min_desc,
                "atividade_descompressao": ativ_desc,
                "diario_tcc_pensamento": p_tcc,
                "diario_tcc_reenquadramento": r_tcc
            }
            if db.salvar_registro_mental(dados_m):
                st.success("Diário de saúde mental atualizado!")
                st.rerun()
