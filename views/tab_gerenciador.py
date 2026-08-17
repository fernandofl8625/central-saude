import streamlit as st


def render_tab_gerenciador(db, metas_user):
    sub_c1, sub_c2, sub_c3, sub_c4, sub_c5 = st.tabs(
        ["💧/☕/⚡ Consumo", "🏃 Modalidades", "💊 Suplementos & Medicamentos", "🎯 Metas & Limites", "📋 Fichas de Treino"])

    with sub_c1:
        st.subheader(
            "⚙️ Personalizar Atalhos de Água, Café, Energético ou Refrigerante")
        with st.form("form_novo_recipiente"):
            col_cad1, col_cad2, col_cad3, col_cad4 = st.columns([2, 3, 2, 2])
            tipo_novo = col_cad1.selectbox("Categoria", [
                                           "agua", "cafeina"], format_func=lambda x: "💧 Água" if x == "agua" else "☕/⚡/🥤 Bebida Estimulante")
            nome_novo = col_cad2.text_input(
                "Nome do Recipiente / Bebida", placeholder="Ex: Lata RedBull 250ml")
            vol_novo = col_cad3.number_input(
                "Volume (ml)", min_value=1, max_value=5000, value=250, step=10)

            categoria_estimulante = col_cad4.selectbox("Tipo de Bebida (Cafeína)", [
                "Café (0.6 mg/ml)",
                "Energético (0.32 mg/ml)",
                "Refrigerante (0.10 mg/ml)",
                "Chá Mate/Preto (0.20 mg/ml)",
                "Sem Cafeína (0.0 mg/ml)"
            ], disabled=(tipo_novo == "agua"))

            fator_calc = 0.0
            if tipo_novo == "cafeina":
                if "Café" in categoria_estimulante:
                    fator_calc = 0.6
                elif "Energético" in categoria_estimulante:
                    fator_calc = 0.32
                elif "Refrigerante" in categoria_estimulante:
                    fator_calc = 0.10
                elif "Chá" in categoria_estimulante:
                    fator_calc = 0.20

            if st.form_submit_button("➕ Salvar Novo Atalho de Consumo"):
                if nome_novo:
                    db.salvar_recipiente(
                        tipo_novo, nome_novo, vol_novo, fator_calc)
                    st.success(f"Atalho '{nome_novo}' cadastrado!")
                    st.rerun()

        st.markdown("---")
        st.subheader("📋 Atalhos Atuais de Consumo")
        rec_agua = db.buscar_recipientes("agua") or []
        rec_cafe = db.buscar_recipientes("cafeina") or []

        col_l1, col_l2 = st.columns(2)
        with col_l1:
            st.markdown("### 💧 Recipientes de Água")
            for r in rec_agua:
                ca, cb = st.columns([3, 1])
                ca.write(f"• **{r['nome']}**: `{r['volume_ml']} ml`")
                if cb.button("🗑️", key=f"del_a_{r['id']}"):
                    db.deletar_recipiente(r['id'])
                    st.rerun()

        with col_l2:
            st.markdown("### ☕/⚡/🥤 Bebidas Estimulantes")
            for r in rec_cafe:
                ca, cb = st.columns([3, 1])
                fator = r.get('fator_cafeina', 0.6) or 0.6
                mg_est = int(r['volume_ml'] * fator)
                ca.write(
                    f"• **{r['nome']}**: `{r['volume_ml']} ml` (~{mg_est}mg cafeína)")
                if cb.button("🗑️", key=f"del_c_{r['id']}"):
                    db.deletar_recipiente(r['id'])
                    st.rerun()

    with sub_c2:
        st.subheader("⚙️ Cadastrar Nova Modalidade de Exercício")
        with st.form("form_nova_modalidade"):
            mc1, mc2 = st.columns([1, 3])
            icone_mod = mc1.text_input("Ícone / Emoji", value="🤸")
            nome_mod = mc2.text_input(
                "Nome da Modalidade", placeholder="Ex: Crossfit, Jiu-Jitsu, Pilates")

            p1, p2, p3 = st.columns(3)
            pede_dist = p1.checkbox("Distância (km)", value=False)
            pede_pace = p2.checkbox("Pace (min/km)", value=False)
            pede_bpm = p3.checkbox("Frequência Cardíaca", value=True)

            if st.form_submit_button("➕ Salvar Modalidade"):
                if nome_mod:
                    db.salvar_modalidade(
                        nome_mod, icone_mod, pede_dist, pede_pace, pede_bpm)
                    st.success(f"Modalidade '{nome_mod}' cadastrada!")
                    st.rerun()

        st.markdown("---")
        mods = db.buscar_modalidades() or []
        for m in mods:
            cm1, cm2 = st.columns([4, 1])
            cm1.write(
                f"**{m['icone']} {m['nome']}** — *(Distância: {'Sim' if m['pede_distancia'] else 'Não'} | Pace: {'Sim' if m['pede_pace'] else 'Não'})*")
            if cm2.button("🗑️ Excluir", key=f"del_mod_{m['id']}"):
                db.deletar_modalidade(m['id'])
                st.rerun()

    with sub_c3:
        st.subheader("⚙️ Cadastrar Novo Suplemento ou Medicamento")
        with st.form("form_novo_suplemento_avancado"):
            cs1, cs2, cs3 = st.columns([3, 2, 2])
            nome_sup = cs1.text_input(
                "Nome do Item / Fármaco", placeholder="Ex: Magnésio Inositol, Creatina")
            dose_sup = cs2.text_input("Dose", placeholder="Ex: 5g, 300mg")
            horario_sup = cs3.selectbox("Horário Recomendado", [
                                        "Manhã", "Almoço", "Tarde", "Pós-Treino", "Noite (Pré-Sono)"])

            cs4, cs5 = st.columns([2, 3])
            cat_acao = cs4.selectbox("Categoria / Efeito Principal", [
                "Indutor de Sono / Relaxante",
                "Estimulante / Energético",
                "Recuperação Muscular / Força",
                "Nootrópico / Foco Mental",
                "Saúde Cardiovascular / Antioxidante",
                "Protetor Gástrico / Digestivo",
                "Medicamento Contínuo"
            ])
            mecanismo_txt = cs5.text_input(
                "Mecanismo / Influência no Dia a Dia", placeholder="Ex: Ativa o GABA...")

            if st.form_submit_button("➕ Salvar Item no Protocolo"):
                if nome_sup and dose_sup:
                    db.salvar_suplemento_custom(
                        nome_sup, dose_sup, horario_sup, cat_acao, mecanismo_txt)
                    st.success(f"Item '{nome_sup}' salvo no protocolo!")
                    st.rerun()

        st.markdown("---")
        sups_cadastrados = db.buscar_suplementos_cadastrados() or []
        for s in sups_cadastrados:
            cs_a, cs_b = st.columns([4, 1])
            cs_a.write(
                f"💊 **{s['nome']}** (`{s['dose']}`) — *{s['horario']}* | **Classe:** `{s.get('categoria_acao', 'Geral')}`\n\n*Mecanismo:* {s.get('mecanismo', 'Sem descrição')}")
            if cs_b.button("🗑️ Excluir", key=f"del_sup_cfg_{s['id']}"):
                db.deletar_suplemento_custom(s['id'])
                st.rerun()

    with sub_c4:
        st.subheader("🎯 Definir Suas Metas & Limites Diários")

        c_ia_meta1, c_ia_meta2 = st.columns([3, 2])
        c_ia_meta1.caption(
            "🤖 **Sugestão Dinâmica por IA:** A IA pode recalcular suas metas com base na sua média real dos últimos 14 dias.")
        if c_ia_meta2.button("✨ Recalcular Metas Diárias com IA", type="primary"):
            df_hist = db.buscar_historico_telemetria(14)
            if not df_hist.empty:
                med_p = int(df_hist['Passos'].fillna(0).mean())
                med_s = round(float(df_hist['HorasSono'].fillna(0).mean()), 1)
                med_sc = int(df_hist['QualidadeSonoScore'].fillna(0).mean())
                peso_ult = float(df_hist['PesoKG'].dropna(
                ).iloc[0]) if not df_hist['PesoKG'].dropna().empty else 92.0

                # Recálculo fisiológico
                nova_meta_passos = max(
                    5000, min(15000, int(med_p * 1.15)))  # Progresso de 15%
                nova_meta_sono = max(7.0, med_s)
                nova_meta_score = max(75, med_sc)
                nova_meta_agua = int(peso_ult * 35)

                db.salvar_meta_config('meta_passos', str(nova_meta_passos))
                db.salvar_meta_config('meta_sono_horas', str(nova_meta_sono))
                db.salvar_meta_config('meta_score_sono', str(nova_meta_score))
                db.salvar_meta_config('meta_agua_fixa_ml', str(nova_meta_agua))

                st.success(
                    f"Metas recalculadas com IA! Nova meta de passos: {nova_meta_passos:,} | Água: {nova_meta_agua}ml")
                st.rerun()

        st.markdown("---")

        with st.form("form_config_metas"):
            m_passos = st.number_input("Meta de Passos Diários", min_value=1000, max_value=50000, value=int(
                metas_user.get('meta_passos', 8000)), step=500)
            m_col1, m_col2 = st.columns(2)
            m_sono_h = m_col1.number_input("Meta de Horas de Sono (h)", min_value=4.0, max_value=12.0, value=float(
                metas_user.get('meta_sono_horas', 7.0)), step=0.5)
            m_sono_score = m_col2.number_input("Meta de Score de Sono", min_value=50, max_value=100, value=int(
                metas_user.get('meta_score_sono', 75)), step=5)
            m_cafe_lim = st.number_input("Teto Máximo de Bebidas Estimulantes (ml)", min_value=50, max_value=2000, value=int(
                metas_user.get('limite_cafe_ml', 300)), step=50)

            st.markdown("---")
            agua_auto = st.checkbox("Calcular meta de água automaticamente baseada no peso corporal (35 ml / kg)",
                                    value=bool(metas_user.get('meta_agua_auto', 1)))
            agua_fixa = st.number_input("Meta Hídrica Fixa (ml)", min_value=1000, max_value=10000, value=int(
                metas_user.get('meta_agua_fixa_ml', 2500)), step=250)

            if st.form_submit_button("💾 Salvar Novas Metas"):
                db.salvar_meta_config('meta_passos', str(m_passos))
                db.salvar_meta_config('meta_sono_horas', str(m_sono_h))
                db.salvar_meta_config('meta_score_sono', str(m_sono_score))
                db.salvar_meta_config('limite_cafe_ml', str(m_cafe_lim))
                db.salvar_meta_config(
                    'meta_agua_auto', '1' if agua_auto else '0')
                db.salvar_meta_config('meta_agua_fixa_ml', str(agua_fixa))
                st.success("Metas salvas com sucesso!")
                st.rerun()

    with sub_c5:
        st.subheader("⚙️ Cadastrar Template / Ficha de Treino Pré-definida")
        modalidades_cadastradas = [m['nome'] for m in db.buscar_modalidades()] or [
            "Musculação", "Corrida", "Caminhada"]

        with st.form("form_nova_ficha_treino"):
            f_c1, f_c2 = st.columns([3, 2])
            nome_ficha_in = f_c1.text_input(
                "Nome do Template / Ficha", placeholder="Ex: Treino A - Peito & Tríceps")
            mod_ficha_in = f_c2.selectbox(
                "Modalidade", modalidades_cadastradas)

            f_c3, f_c4, f_c5, f_c6 = st.columns(4)
            duracao_est = f_c3.number_input(
                "Duração Est. (min)", min_value=5, max_value=300, value=50, step=5)
            calorias_est = f_c4.number_input(
                "Calorias Est. (kcal)", min_value=0, max_value=3000, value=300, step=25)
            bpm_est = f_c5.number_input(
                "FC Média Alvo (BPM)", min_value=40, max_value=220, value=120, step=1)
            pse_est = f_c6.slider("PSE Alvo (0-10)", 0, 10, 6)

            exercicios_txt = st.text_area(
                "Lista de Exercícios / Séries", placeholder="Ex:\n- Supino Reto (4x10)...")

            if st.form_submit_button("➕ Salvar Template de Treino"):
                if nome_ficha_in:
                    if db.salvar_ficha_treino(nome_ficha_in, mod_ficha_in, duracao_est, calorias_est, bpm_est, pse_est, exercicios_txt):
                        st.success(
                            f"Template '{nome_ficha_in}' salvo com sucesso!")
                        st.rerun()

        st.markdown("---")
        fichas_salvas = db.buscar_fichas_treino() or []
        for f in fichas_salvas:
            c_f1, c_f2 = st.columns([4, 1])
            info_f = f"**{f['nome_ficha']}** (`{f['modalidade']}`) — `{f['duracao_est_min']} min` | `{f['calorias_est_kcal']} kcal` | `FC: {f['bpm_medio_est']} BPM` | `PSE: {f['pse_est']}/10`"
            if f['exercicios_detalhe']:
                info_f += f"\n\n*Exercícios:* {f['exercicios_detalhe']}"
            c_f1.markdown(info_f)
            if c_f2.button("🗑️ Excluir", key=f"del_ficha_{f['id']}"):
                db.deletar_ficha_treino(f['id'])
                st.rerun()
