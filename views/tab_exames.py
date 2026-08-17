from datetime import date, datetime
import pandas as pd
import streamlit as st


def render_tab_exames(db):
    st.subheader("🩺 Leitor & Monitor de Exames Laboratoriais (Sabin / Fleury)")
    st.caption(
        "Upload inteligente de exames em PDF com monitoramento automático de valores fora de referência.")

    # --- 1. UPLOAD E PARSER DE EXAMES ---
    files_pdf = st.file_uploader(
        "Arraste um ou mais PDFs do Sabin/Fleury aqui", type=["pdf"], accept_multiple_files=True)

    if files_pdf:
        all_exames_extraidos = []
        data_coleta_detectada = ""

        for file_pdf in files_pdf:
            texto_raw, data_col = db._extrair_texto_pdf_exame(
                file_pdf) if hasattr(db, '_extrair_texto_pdf_exame') else ("", "")
            if data_col:
                data_coleta_detectada = data_col
            if texto_raw:
                exames_sabin = db._parse_exames_sabin_especifico(
                    texto_raw) if hasattr(db, '_parse_exames_sabin_especifico') else []
                all_exames_extraidos.extend(exames_sabin)

        st.markdown("---")
        st.subheader("📋 Marcadores Detectados no Arquivo")

        if not all_exames_extraidos:
            st.warning(
                "Nenhum marcador padronizado do Sabin detectado. Verifique se o PDF não é uma imagem escaneada.")
        else:
            st.success(
                f"🎉 {len(all_exames_extraidos)} exames extraídos com sucesso!")
            df_para_editor = pd.DataFrame(all_exames_extraidos)

            with st.form("form_confirmar_exames_sabin"):
                c_e1, c_e2 = st.columns(2)

                default_date = date.today()
                if data_coleta_detectada:
                    try:
                        default_date = datetime.strptime(
                            data_coleta_detectada, "%d/%m/%Y").date()
                    except ValueError:
                        pass

                data_exame_cad = c_e1.date_input(
                    "Data da Coleta do Exame", value=default_date)
                lab_cad = c_e2.text_input(
                    "Laboratório / Origem", value="Sabin")

                st.write(
                    "✏️ **Revise e confirme os valores antes de salvar no banco:**")
                df_editado = st.data_editor(
                    df_para_editor,
                    num_rows="dynamic",
                    width="stretch"
                )

                if st.form_submit_button("💾 Confirmar e Salvar Todos no Banco"):
                    if db.salvar_exames_lote(data_exame_cad.strftime('%Y-%m-%d'), lab_cad, df_editado):
                        st.success(
                            "Exames do Sabin gravados no banco com sucesso!")
                        st.rerun()

    st.markdown("---")

    # --- 2. ALERTAS DE MARCADORES FORA DA FAIXA DE REFERÊNCIA ---
    df_exames_db = db.buscar_historico_exames()

    if not df_exames_db.empty:
        st.markdown("#### 🚨 Central de Alertas & Referências Laboratoriais")

        # Filtrar exames da coleta mais recente
        data_mais_recente = df_exames_db['data_exame'].max()
        df_recente = df_exames_db[df_exames_db['data_exame']
                                  == data_mais_recente]

        foras_ref = []
        for _, row in df_recente.iterrows():
            res = float(row['resultado'])
            rmin = float(row['referencia_min']) if pd.notnull(
                row['referencia_min']) else None
            rmax = float(row['referencia_max']) if pd.notnull(
                row['referencia_max']) else None

            if rmin is not None and res < rmin:
                foras_ref.append(
                    (row['marcador'], res, row['unidade'], f"Abaixo do mínimo ({rmin})", "warning"))
            elif rmax is not None and res > rmax:
                foras_ref.append(
                    (row['marcador'], res, row['unidade'], f"Acima do máximo ({rmax})", "danger"))

        if foras_ref:
            st.caption(
                f"Exames analisados da coleta de `{data_mais_recente}`:")
            cols_alertas = st.columns(min(len(foras_ref), 4))
            for idx, (m_nome, m_res, m_und, m_status, m_nivel) in enumerate(foras_ref):
                col_target = cols_alertas[idx % len(cols_alertas)]
                msg_card = f"**{m_nome}**: `{m_res} {m_und or ''}`\n\n*Status:* {m_status}"
                if m_nivel == "danger":
                    col_target.error(msg_card)
                else:
                    col_target.warning(msg_card)
        else:
            st.success(
                f"✅ Todos os marcadores da coleta de `{data_mais_recente}` estão dentro das faixas normais de referência!")

        st.markdown("---")

        # --- 3. ANÁLISE TEMPORAL POR MARCADOR ---
        c_aud1, c_aud2 = st.columns([3, 1])
        c_aud1.markdown("#### 📈 Evolução Histórica de Marcador Específico")

        if c_aud2.button("🧹 Limpar Duplicatas", key="btn_auditar_exames"):
            if db.limpar_exames_duplicados_banco():
                st.success("Registros duplicados removidos com sucesso!")
                st.rerun()

        marcadores_unicos = df_exames_db['marcador'].unique().tolist()
        marcador_sel = st.selectbox(
            "Selecione um Marcador Laboratorial:", options=marcadores_unicos, index=0)

        df_marcador = df_exames_db[df_exames_db['marcador']
                                   == marcador_sel].sort_values(by="data_exame")

        if len(df_marcador) >= 2:
            ult_res = float(df_marcador.iloc[-1]['resultado'])
            prev_res = float(df_marcador.iloc[-2]['resultado'])
            delta_val = ult_res - prev_res
            st.metric(f"Último Valor ({marcador_sel})",
                      f"{ult_res} {df_marcador.iloc[-1]['unidade'] or ''}", delta=f"{delta_val:+.2f}")

        st.line_chart(df_marcador.set_index("data_exame")[["resultado"]])

        with st.expander("📋 Ver Tabela Completa de Exames Salvos no Banco"):
            st.dataframe(df_exames_db, width="stretch")

            m_del = st.number_input(
                "ID do registro para excluir:", min_value=1, step=1, value=1)
            if st.button("🗑️ Excluir Registro"):
                db.deletar_exame(m_del)
                st.rerun()
    else:
        st.info("Nenhum exame cadastrado no banco de dados ainda.")
