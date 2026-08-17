from datetime import date
import streamlit as st


def render_tab_lancamentos(db, ai_assistant, metas_user):
    data_reg = st.date_input("📅 Data de Referência", value=date.today())
    data_str = data_reg.strftime('%Y-%m-%d')
    reg_atual = db.buscar_registro_por_data(data_str) or {}

    # --- CARD 1: DIÁRIO SINTOMÁTICO ---
    with st.expander("🧠 1. Diário Sintomático (Disposição, Foco, Dor & Digestão)", expanded=False):
        st.subheader(f"🩺 Percepções Qualitativas do Dia ({data_str})")
        st.caption(
            "Avalie como você se sentiu hoje (escala de 0 a 10) para cruzar com sono, exames e suplementos:")

        with st.form("form_diario_sintomatico"):
            sint_c1, sint_c2 = st.columns(2)
            disp_val = sint_c1.slider("⚡ Disposição ao Acordar (0 = Exausto, 10 = Energia Total)", 0, 10, int(
                reg_atual.get('DisposicaoAcordarScore') or 5))
            foco_val = sint_c2.slider("🧠 Clareza Mental & Foco (0 = Névoa, 10 = Nítido)", 0, 10, int(
                reg_atual.get('FocoClarezaScore') or 5))

            sint_c3, sint_c4 = st.columns(2)
            dor_val = sint_c3.slider("🦴 Dor Muscular / Articular - DOMS (0 = Sem dor, 10 = Dor Forte)",
                                     0, 10, int(reg_atual.get('DorMuscularScore') or 0))
            diges_val = sint_c4.slider("🫄 Conforto Digestivo (0 = Inchaço/Desconforto, 10 = Excelente)",
                                       0, 10, int(reg_atual.get('ConfortoDigestivoScore') or 8))

            if st.form_submit_button("💾 Salvar Percepções Sintomáticas"):
                score_s = int(reg_atual.get('QualidadeSonoScore', 75) or 75)
                spo2_s = float(reg_atual.get('SpO2MedioPct', 96.5) or 96.5)
                fc_s = int(reg_atual.get(
                    'FrequenciaCardiacaRepouso', 62) or 62)
                prof_s = int(reg_atual.get('SonoProfundoMinutos', 60) or 60)
                rem_s = int(reg_atual.get('SonoREMMinutos', 90) or 90)
                tot_min = float(reg_atual.get('HorasSono', 7.0) or 7.0) * 60

                pct_prof = (prof_s / tot_min * 100) if tot_min > 0 else 0
                pct_r = (rem_s / tot_min * 100) if tot_min > 0 else 0

                new_readiness = int(
                    (score_s * 0.3) +
                    (min(100, (spo2_s - 90) * 10) * 0.15) +
                    (min(100, max(0, 100 - (fc_s - 50) * 2)) * 0.15) +
                    (min(100, (pct_prof + pct_r) * 2) * 0.15) +
                    (disp_val * 10 * 0.15) +
                    (max(0, 100 - (dor_val * 10)) * 0.10)
                )

                if db.atualizar_secao_parcial(data_str, {
                    "DisposicaoAcordarScore": disp_val,
                    "FocoClarezaScore": foco_val,
                    "DorMuscularScore": dor_val,
                    "ConfortoDigestivoScore": diges_val,
                    "ScoreProntitudade": new_readiness
                }):
                    st.success(
                        f"Percepções salvas! Readiness atualizado para `{new_readiness}/100`.")
                    st.rerun()

    # --- CARD 2: ARQUITETURA DO SONO & RECUPERAÇÃO CARDIO (GALAXY WATCH 4) ---
    with st.expander("😴 2. Arquitetura do Sono & Recuperação Cardio (Galaxy Watch 4)", expanded=False):
        st.caption(
            "Insira os dados detalhados coletados pelo aplicativo Samsung Health:")

        with st.form("form_sono_watch4"):
            st.markdown("##### ⏱️ 1. Duração & Estágios do Sono")
            s1, s2, s3, s4 = st.columns(4)
            horas_sono = s1.number_input("Horas de Sono Totais", min_value=0.0, max_value=24.0, value=float(
                reg_atual.get('HorasSono') or 7.0), step=0.25)
            score_sono = s2.slider(
                "Score de Sono (0-100)", 0, 100, int(reg_atual.get('QualidadeSonoScore') or 75))
            sono_profundo = s3.number_input("Sono Profundo (minutos)", min_value=0, max_value=600, value=int(
                reg_atual.get('SonoProfundoMinutos') or 60), step=5)
            sono_rem = s4.number_input("Sono REM (minutos)", min_value=0, max_value=600, value=int(
                reg_atual.get('SonoREMMinutos') or 90), step=5)

            st.markdown("---")
            st.markdown(
                "##### 🫁 2. Métricas Cardiorrespiratórias & Fisiologia Noturna")
            s5, s6, s7, s8 = st.columns(4)
            frequencia_repouso = s5.number_input("FC Média em Repouso (BPM)", min_value=30, max_value=150, value=int(
                reg_atual.get('FrequenciaCardiacaRepouso') or 62), step=1)
            spo2_medio = s6.number_input("SpO₂ Médio Noturno (%)", min_value=70.0, max_value=100.0, value=float(
                reg_atual.get('SpO2MedioPct') or 96.5), step=0.5)
            freq_resp = s7.number_input("Freq. Respiratoria (mora/min)", min_value=8.0, max_value=30.0,
                                        value=float(reg_atual.get('FreqRespiratoriaMedio') or 14.5), step=0.5)
            latencia = s8.number_input("Latencia do Sono (min)", min_value=0, max_value=120, value=int(
                reg_atual.get('LatenciaSonoMinutos') or 15), step=1)

            tempo_sono_min = horas_sono * 60
            pct_profundo = (sono_profundo / tempo_sono_min *
                            100) if tempo_sono_min > 0 else 0
            pct_rem = (sono_rem / tempo_sono_min *
                       100) if tempo_sono_min > 0 else 0

            disp_hoje = int(reg_atual.get('DisposicaoAcordarScore', 5) or 5)
            dor_doms_hoje = int(reg_atual.get('DorMuscularScore', 0) or 0)

            readiness_calc = int(
                (score_sono * 0.3) +
                (min(100, (spo2_medio - 90) * 10) * 0.15) +
                (min(100, max(0, 100 - (frequencia_repouso - 50) * 2)) * 0.15) +
                (min(100, (pct_profundo + pct_rem) * 2) * 0.15) +
                (disp_hoje * 10 * 0.15) +
                (max(0, 100 - (dor_doms_hoje * 10)) * 0.10)
            )

            st.info(
                f"💡 **Readiness Score Estimado para o Dia:** `{readiness_calc} / 100` *(Calculado a partir do Watch 4 + Disposição ({disp_hoje}/10) e DorMuscular ({dor_doms_hoje}/10))*")

            if st.form_submit_button("💾 Salvar Fisiologia do Sono & Watch 4"):
                if db.atualizar_secao_parcial(data_str, {
                    "HorasSono": horas_sono,
                    "QualidadeSonoScore": score_sono,
                    "FrequenciaCardiacaRepouso": frequencia_repouso,
                    "SonoProfundoMinutos": sono_profundo,
                    "SonoREMMinutos": sono_rem,
                    "LatenciaSonoMinutos": latencia,
                    "SpO2MedioPct": spo2_medio,
                    "FreqRespiratoriaMedio": freq_resp,
                    "ScoreProntitudade": readiness_calc
                }):
                    st.success(
                        "Fisiologia do Sono & Watch 4 salvos com sucesso!")
                    st.rerun()

    # --- CARD 3: SUPLEMENTAÇÃO, MEDICAMENTOS & CHECKLIST DIÁRIO ---
    with st.expander("💊 3. Suplementação, Medicamentos & Checklist Diário", expanded=False):
        st.subheader(f"📋 Checklist de Suplementos para {data_str}")
        lista_suplementos = db.buscar_suplementos_cadastrados() or []
        logs_hoje = db.buscar_logs_suplementos_data(data_str) or {}

        if not lista_suplementos:
            st.info(
                "Nenhum suplemento cadastrado no sistema ainda. Cadastre na aba '⚙️ Atalhos & Configurações'.")
        else:
            st.caption(
                "Marque os itens à medida que for tomando ao longo do dia:")
            cols_sup = st.columns(len(lista_suplementos)) if len(
                lista_suplementos) <= 4 else st.columns(4)

            for idx, sup in enumerate(lista_suplementos):
                sup_id = sup['id']
                ja_tomou = logs_hoje.get(sup_id, False)
                col_target = cols_sup[idx % len(cols_sup)]

                label_chk = f"**{sup['nome']}**\n\n`{sup['dose']}` | *{sup['horario']}*\n\nClasse: `{sup.get('categoria_acao', 'Geral')}`"
                checked = col_target.checkbox(
                    label_chk, value=ja_tomou, key=f"chk_sup_{data_str}_{sup_id}")

                if checked != ja_tomou:
                    db.salvar_log_suplemento(data_str, sup_id, checked)
                    st.rerun()

    # --- CARD 4: ATIVIDADE FÍSICA, PASSOS & SESSÕES DE TREINO ---
    with st.expander("🏃 4. Atividade Física, Passos & Sessões de Treino", expanded=False):
        st.subheader("📊 Agregado Diário de Passos & Atividade")
        with st.form("form_atividade_diaria"):
            c1, c2, c3 = st.columns(3)
            passos = c1.number_input("Passos Totais do Dia", min_value=0, max_value=100000, value=int(
                reg_atual.get('Passos') or 0), step=500)
            calorias_diarias = c2.number_input("Calorias Ativas Totais (kcal)", min_value=0, max_value=10000, value=int(
                reg_atual.get('CaloriasQueimadas') or 0), step=50)
            minutos_diarios = c3.number_input("Minutos Ativos Totais", min_value=0, max_value=1440, value=int(
                reg_atual.get('MinutosAtivos') or 0), step=5)

            if st.form_submit_button("💾 Salvar Totais do Dia"):
                if db.atualizar_secao_parcial(data_str, {
                    "Passos": passos,
                    "CaloriasQueimadas": calorias_diarias,
                    "MinutosAtivos": minutos_diarios
                }):
                    st.success("Totais de atividade atualizados!")
                    st.rerun()

        st.markdown("---")
        st.subheader("🏋️ Registrar Sessão de Treino")

        c_presc1, c_presc2 = st.columns([3, 2])
        c_presc1.markdown(
            "💡 **Dica Fisiológica:** Certifique-se de salvar os **Card 1 (Diário Sintomático)**, **Card 2 (Sono)** e a aba **🧠 Saúde Mental** de hoje antes de gerar a prescrição.")
        if c_presc2.button("✨ Prescrever Treino do Dia com Base na Minha Recuperação", type="primary", key="btn_prescrever_treino_card4"):
            with st.spinner("Analisando seu Readiness, Sono do Watch 4, Saúde Mental, Dor muscular (DOMS) e treinos recentes..."):
                try:
                    sugestao = ai_assistant.prescrever_treino_diario(data_str)
                    if sugestao:
                        st.session_state.sugestao_treino_hoje = sugestao
                        st.rerun()
                except Exception as e_ia:
                    st.error(f"Erro ao prescrever treino: {e_ia}")

        dados_sugeridos = st.session_state.get(
            'sugestao_treino_hoje', {}) or {}

        if dados_sugeridos:
            st.success(f"""
            🎯 **Prescrição Adaptativa Gerada pela IA para {data_str}:**
            * **Treino Recomendado:** `{dados_sugeridos.get('nome_sugerido', 'Treino Adaptado')}`
            * **Modalidade:** `{dados_sugeridos.get('modalidade', 'Musculação')}` | **Duração:** `{dados_sugeridos.get('duracao_min', 45)} min` | **PSE Alvo:** `{dados_sugeridos.get('pse_alvo', 6)}/10`
            * **Exercícios Sugeridos:**\n\n{dados_sugeridos.get('exercicios', '')}
            
            *👇 Os campos abaixo foram preenchidos automaticamente. Revise ou ajuste antes de confirmar:*
            """)

        fichas_disponiveis = db.buscar_fichas_treino() or []
        mapa_fichas = {f['nome_ficha']: f for f in fichas_disponiveis}

        ficha_selecionada = st.selectbox(
            "⚡ Ou Escolha um Template Pré-definido da Sua Lista",
            options=["-- Seleção Manual / Prescrição IA --"] +
            list(mapa_fichas.keys()),
            index=0,
            key="sel_template_ficha_card4"
        )

        dados_template = mapa_fichas.get(ficha_selecionada, {}) or {}

        dur_padrao = dados_sugeridos.get('duracao_min') if dados_sugeridos.get('duracao_min') is not None else (
            dados_template.get('duracao_est_min') if dados_template.get('duracao_est_min') is not None else 45)
        cal_padrao = dados_sugeridos.get('calorias_kcal') if dados_sugeridos.get('calorias_kcal') is not None else (
            dados_template.get('calorias_est_kcal') if dados_template.get('calorias_est_kcal') is not None else 250)
        bpm_padrao = dados_sugeridos.get('bpm_alvo') if dados_sugeridos.get('bpm_alvo') is not None else (
            dados_template.get('bpm_medio_est') if dados_template.get('bpm_medio_est') is not None else 125)
        pse_padrao = dados_sugeridos.get('pse_alvo') if dados_sugeridos.get('pse_alvo') is not None else (
            dados_template.get('pse_est') if dados_template.get('pse_est') is not None else 5)
        mod_padrao = dados_sugeridos.get(
            'modalidade') or dados_template.get('modalidade') or 'Musculação'
        notas_padrao = dados_sugeridos.get(
            'exercicios') or dados_template.get('exercicios_detalhe') or ''

        dist_padrao = float(dados_sugeridos.get('distancia_km') or 0.0)
        pace_padrao = str(dados_sugeridos.get('pace_medio') or "5:30")
        bpm_max_padrao = int(dados_sugeridos.get(
            'bpm_max') or (bpm_padrao + 20))

        modalidades_lista = db.buscar_modalidades() or []
        mapa_modalidades = {m['nome']: m for m in modalidades_lista}
        opcoes_modalidade = list(mapa_modalidades.keys()) if mapa_modalidades else [
            "Musculação"]

        idx_mod = 0
        if mod_padrao and mod_padrao in opcoes_modalidade:
            idx_mod = opcoes_modalidade.index(mod_padrao)

        nome_mod_sel = st.selectbox(
            "Modalidade do Treino", opcoes_modalidade, index=idx_mod, key="sel_mod_treino_card4")
        mod_config = mapa_modalidades.get(
            nome_mod_sel, {'icone': '🏋️', 'pede_distancia': 0, 'pede_pace': 0, 'pede_bpm': 1})

        with st.form("form_novo_treino_card4"):
            t1, t2, t3 = st.columns(3)
            duracao = t1.number_input(
                "Duração (minutos)", min_value=1, max_value=600, value=int(dur_padrao or 45), step=5)
            calorias_treino = t2.number_input(
                "Calorias do Treino (kcal)", min_value=0, max_value=5000, value=int(cal_padrao or 250), step=25)
            bpm_medio = t3.number_input(
                "FC Média (BPM)", min_value=30, max_value=220, value=int(bpm_padrao or 125), step=1)

            distancia = dist_padrao
            pace = pace_padrao
            bpm_max = bpm_max_padrao

            if mod_config.get('pede_distancia') or mod_config.get('pede_pace'):
                d1, d2, d3 = st.columns(3)
                distancia = d1.number_input("Distância (km)", min_value=0.0, max_value=300.0,
                                            value=dist_padrao, step=0.1) if mod_config.get('pede_distancia') else 0.0
                pace = d2.text_input("Pace Médio (min/km)", value=pace_padrao,
                                     placeholder="Ex: 5:30") if mod_config.get('pede_pace') else ""
                bpm_max = d3.number_input(
                    "FC Máxima (BPM)", min_value=30, max_value=220, value=int(bpm_max_padrao), step=1)
            else:
                d1, d2 = st.columns(2)
                bpm_max = d1.number_input(
                    "FC Máxima (BPM)", min_value=30, max_value=220, value=int(bpm_max_padrao), step=1)

            st.markdown("---")
            st.write("🧠 **Sensação & Percepção Pós-Atividade Física:**")
            e1, e2 = st.columns(2)
            sensacao_pos = e1.slider(
                "Esforço Percebido / Cansaço Pós-Treino (0 = Leve, 10 = Exaustão)", 0, 10, int(pse_padrao or 5))
            sintomas_pos = e2.text_input("Sintomas ou Percepções Pós-Treino",
                                         placeholder="Ex: Pump excelente, Leveza, Tontura, Fadiga muscular")

            notas = st.text_area("Notas / Exercícios Executados", value=notas_padrao,
                                 placeholder="Ex: Treino de Peito/Tríceps ou Pista do Parque")

            if st.form_submit_button("➕ Confirmar e Registrar Treino"):
                dados_treino = {
                    "data_registro": data_str,
                    "modalidade": nome_mod_sel,
                    "duracao_minutos": duracao,
                    "calorias_queimadas": calorias_treino,
                    "distancia_km": distancia,
                    "pace_medio": pace,
                    "bpm_medio": bpm_medio,
                    "bpm_maximo": bpm_max,
                    "sensacao_pos_treino": sensacao_pos,
                    "sintomas_pos_treino": sintomas_pos,
                    "notas_treino": notas
                }
                if db.salvar_sessao_treino(dados_treino):
                    if 'sugestao_treino_hoje' in st.session_state:
                        del st.session_state['sugestao_treino_hoje']
                    st.success(f"Sessão de {nome_mod_sel} registrada!")
                    st.rerun()

        st.markdown("---")
        st.subheader(f"📋 Treinos Registrados em {data_str}")
        sessoes = db.buscar_sessoes_treino(data_str) or []
        if not sessoes:
            st.info("Nenhum treino registrado para esta data ainda.")
        else:
            for s in sessoes:
                col_t1, col_t2 = st.columns([5, 1])
                ic = mapa_modalidades.get(
                    s['modalidade'], {}).get('icone', '🏋️')
                info_str = f"**{ic} {s['modalidade']}** — `{s['duracao_minutos']} min` | `{s['calorias_queimadas']} kcal` | `FC Méd: {s['bpm_medio']} BPM` | `PSE: {s.get('sensacao_pos_treino', 5)}/10`"
                if s.get('distancia_km', 0) > 0:
                    info_str += f" | `{s['distancia_km']} km`"
                if s.get('pace_medio'):
                    info_str += f" | `Pace: {s['pace_medio']}`"
                if s.get('sintomas_pos_treino'):
                    info_str += f"\n\n*Pós-Treino:* {s['sintomas_pos_treino']}"
                if s.get('notas_treino'):
                    info_str += f"\n\n*Nota:* {s['notas_treino']}"

                col_t1.markdown(info_str)
                if col_t2.button("🗑️ Excluir", key=f"del_treino_{s['id']}"):
                    db.deletar_sessao_treino(s['id'])
                    st.rerun()

    # --- CARD 5: INGESTÃO HÍDRICA & BEBIDAS ESTIMULANTES ---
    with st.expander("💧 5. Ingestão Hídrica & Bebidas Estimulantes", expanded=False):
        peso_atual_rec = float(reg_atual.get('PesoKG') or 92.0)
        meta_agua = int(peso_atual_rec * 35) if metas_user.get('meta_agua_auto',
                                                               1) else metas_user.get('meta_agua_fixa_ml', 2500)
        limite_cafeina = metas_user.get('limite_cafe_ml', 300)

        agua_atual = int(reg_atual.get('ConsumoAguaML') or 0)
        cafe_atual = int(reg_atual.get('ConsumoCafeML') or 0)
        cafeina_atual = int(reg_atual.get('ConsumoCafeinaMG') or 0)

        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.markdown(
                f"**💧 Hidratação Diária:** `{agua_atual} / {meta_agua} ml`", unsafe_allow_html=True)
            pct_agua = min(1.0, agua_atual /
                           meta_agua) if meta_agua > 0 else 0.0
            st.progress(pct_agua)

            total_garrafas = 6
            garrafas_cheias = int(pct_agua * total_garrafas)
            garrafas_html = "".join(
                [" 🍾 " if i < garrafas_cheias else " 🫙 " for i in range(total_garrafas)])
            st.caption(
                f"**Nível:** {garrafas_html} *({garrafas_cheias}/{total_garrafas} garrafas recomendadas)*")

        with col_m2:
            st.markdown(
                f"**⚡ Estimulantes Líquidos:** `{cafe_atual} / {limite_cafeina} ml` (~{cafeina_atual}mg cafeína)", unsafe_allow_html=True)
            pct_cafe = min(1.0, cafe_atual /
                           limite_cafeina) if limite_cafeina > 0 else 0.0
            st.progress(pct_cafe)

            total_xicaras = 4
            xicaras_cheias = int(pct_cafe * total_xicaras)

            if cafe_atual > limite_cafeina:
                xicaras_html = " ⚠️ " * total_xicaras
                st.caption(
                    f"**Atenção:** {xicaras_html} *(Teto máximo recomendado ultrapassado!)*")
            else:
                xicaras_html = "".join(
                    [" ☕ " if i < xicaras_cheias else " 🫖 " for i in range(total_xicaras)])
                st.caption(
                    f"**Consumo:** {xicaras_html} *({xicaras_cheias}/{total_xicaras} doses do dia)*")

        st.markdown("---")
        col_at1, col_at2 = st.columns([3, 1])
        col_at1.caption("⚡ **Atalhos Rápidos de Consumo (+ Somar ao Dia):**")
        if col_at2.button("🔄 Zerar Consumos de Hoje", key="btn_zerar_consumos_hoje"):
            db.atualizar_secao_parcial(
                data_str, {"ConsumoAguaML": 0, "ConsumoCafeML": 0, "ConsumoCafeinaMG": 0})
            st.success("Consumos de água e bebidas zerados para hoje!")
            st.rerun()

        recipientes_agua = db.buscar_recipientes("agua") or []
        st.write("💧 **Adicionar Água:**")
        if recipientes_agua:
            cols_agua = st.columns(len(recipientes_agua))
            for idx, rec in enumerate(recipientes_agua):
                if cols_agua[idx].button(f"➕ {rec['nome']} ({rec['volume_ml']}ml)", key=f"btn_agua_fast_{rec['id']}"):
                    atual = int(reg_atual.get('ConsumoAguaML') or 0)
                    db.atualizar_secao_parcial(
                        data_str, {"ConsumoAguaML": atual + rec['volume_ml']})
                    st.rerun()

        recipientes_cafeina = db.buscar_recipientes("cafeina") or []
        st.write("☕/⚡/🥤 **Adicionar Café, Energético ou Refrigerante:**")
        if recipientes_cafeina:
            cols_cafe = st.columns(len(recipientes_cafeina))
            for idx, rec in enumerate(recipientes_cafeina):
                vol_ml = rec['volume_ml']
                fator = rec.get('fator_cafeina', 0.6) or 0.6
                mg_est = int(vol_ml * fator)
                if cols_cafe[idx].button(f"➕ {rec['nome']} (~{mg_est}mg)", key=f"btn_cafe_fast_{rec['id']}"):
                    atual_ml = int(reg_atual.get('ConsumoCafeML') or 0)
                    atual_mg = int(reg_atual.get('ConsumoCafeinaMG') or 0)
                    db.atualizar_secao_parcial(data_str, {
                        "ConsumoCafeML": atual_ml + vol_ml,
                        "ConsumoCafeinaMG": atual_mg + mg_est
                    })
                    st.rerun()

        st.markdown("---")

        with st.form("form_habitos_ajuste"):
            h1, h2, h3, h4 = st.columns(4)
            energia_score = h1.slider(
                "Energia / Bateria (0-100)", 0, 100, int(reg_atual.get('NivelEnergiaScore') or 80))
            estresse_score = h2.slider(
                "Estresse (0-100)", 0, 100, int(reg_atual.get('NivelEstresseScore') or 35))
            consumo_agua_input = h3.number_input(
                "Água Total (ml)", min_value=0, max_value=10000, value=agua_atual, step=250)
            consumo_cafe_input = h4.number_input(
                "Bebidas Estimulantes (ml)", min_value=0, max_value=5000, value=cafe_atual, step=50)

            mg_calculada = int(consumo_cafe_input * 0.6)
            obs = st.text_area("Observações sobre o dia", value=reg_atual.get(
                'Observacoes') or "", placeholder="Notas rápidas...")

            if st.form_submit_button("💾 Salvar Ajuste Manual de Hábitos"):
                if db.atualizar_secao_parcial(data_str, {
                    "NivelEnergiaScore": energia_score,
                    "NivelEstresseScore": estresse_score,
                    "ConsumoAguaML": consumo_agua_input,
                    "ConsumoCafeML": consumo_cafe_input,
                    "ConsumoCafeinaMG": mg_calculada,
                    "Observacoes": obs
                }):
                    st.success(
                        f"Hábitos salvos! Estimulantes: {consumo_cafe_input}ml (~{mg_calculada}mg de cafeína).")
                    st.rerun()

    # --- CARD 6: COMPOSIÇÃO CORPORAL & BIOIMPEDÂNCIA ---
    with st.expander("⚖️ 6. Composição Corporal & Bioimpedância", expanded=False):
        with st.form("form_biometria_expandida"):
            b1, b2, b3 = st.columns(3)
            peso_val = b1.number_input("Peso Total (kg)", min_value=0.0, max_value=300.0, value=float(
                reg_atual.get('PesoKG') or 92.0), step=0.1)
            pct_gordura_val = b2.number_input("Gordura Corporal (%)", min_value=0.0, max_value=100.0, value=float(
                reg_atual.get('PercentualGordura') or 0.0), step=0.1)
            musculo_val = b3.number_input("Músculo Esquelético (kg)", min_value=0.0, max_value=150.0, value=float(
                reg_atual.get('MusculoEsqueleticoKG') or 0.0), step=0.1)

            b4, b5, b6 = st.columns(3)
            massa_gorda_val = b4.number_input("Massa Gorda (kg)", min_value=0.0, max_value=150.0, value=float(
                reg_atual.get('MassaGordaKG') or 0.0), step=0.1)
            agua_corp_val = b5.number_input("Água Corporal (kg)", min_value=0.0, max_value=150.0, value=float(
                reg_atual.get('AguaCorporalKG') or 0.0), step=0.1)
            tmb_val = b6.number_input("Taxa Metabólica Basal - TMB (kcal)", min_value=0,
                                      max_value=5000, value=int(reg_atual.get('TMBKcal') or 0), step=25)

            if st.form_submit_button("💾 Salvar Bioimpedância"):
                if db.atualizar_secao_parcial(data_str, {
                    "PesoKG": peso_val if peso_val > 0 else None,
                    "PercentualGordura": pct_gordura_val if pct_gordura_val > 0 else None,
                    "MusculoEsqueleticoKG": musculo_val if musculo_val > 0 else None,
                    "MassaGordaKG": massa_gorda_val if massa_gorda_val > 0 else None,
                    "AguaCorporalKG": agua_corp_val if agua_corp_val > 0 else None,
                    "TMBKcal": tmb_val if tmb_val > 0 else None
                }):
                    st.success("Composição Corporal atualizada!")
                    st.rerun()
