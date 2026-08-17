import pandas as pd
import numpy as np
import streamlit as st


def render_tab_biometria(db):
    df_peso = db.buscar_historico_telemetria()

    st.subheader("⚖️ Análise Avançada de Composição Corporal & Bioimpedância")

    # --- CARD DE ORIENTAÇÕES E FREQUÊNCIA DE COLETA PARA MAIOR PRECISÃO ---
    with st.expander("💡 **Orientações de Frequência & Padronização das Coletas**", expanded=False):
        st.markdown("""
        Para obter métricas precisas e evitar distorções por retenção hídrica, siga este protocolo de coleta:
        
        * **⚖️ Medição de Peso Diária (ou 3-4x/semana):**
          * **Frequência:** Diária.
          * **Protocolo:** Logo ao acordar, em jejum, após utilizar o banheiro e usando roupas leves.
          * **Por que?** O peso varia diariamente por sódio e água. Acompanhe a **Média Móvel de 7 dias** (linha azul no gráfico) para ver a tendência real.
        
        * **📊 Bioimpedância Completa (% Gordura, Músculo, Água e TMB):**
          * **Frequência:** Quinzenal ou Mensal (a cada 14 a 30 dias).
          * **Protocolo:** Evite treinos intensos nas 12h anteriores, mantenha hidratação constante na véspera e evite bebidas estimulantes/álcool antes da medição.
          * **Por que?** Músculo e gordura levam semanas para ter alteração estrutural real. Medir a bioimpedância diariamente reflete apenas flutuação de fluidos corporais.
        """)

    if df_peso.empty or 'PesoKG' not in df_peso.columns or df_peso['PesoKG'].dropna().empty:
        st.info("💡 **Nenhum registro de bioimpedância encontrado.** Lance os dados de peso e composição na aba Lançamentos para ativar este painel.")
        return

    # Filtrar apenas registros que possuem Peso lançado
    df = df_peso[df_peso['PesoKG'].notnull()].sort_values(
        by="DataRegistro").copy()
    df['DataRegistro'] = pd.to_datetime(df['DataRegistro'])

    ult = df.iloc[-1]  # Leitura mais recente
    penult = df.iloc[-2] if len(df) > 1 else ult  # Leitura anterior

    st.caption(
        f"Última medição registrada em: `{ult['DataRegistro'].strftime('%d/%m/%Y')}`")

    # --- 1. CARDS DE MÉTRICAS PRINCIPAIS ---
    c1, c2, c3, c4 = st.columns(4)

    # Peso Total + Delta em relação ao registro anterior
    delta_peso = round(ult['PesoKG'] - penult['PesoKG'],
                       1) if len(df) > 1 else 0.0
    c1.metric("Peso Total", f"{ult['PesoKG']:.1f} kg",
              delta=f"{delta_peso:+.1f} kg", delta_color="inverse")

    # Músculo Esquelético
    musc_val = ult.get('MusculoEsqueleticoKG') or 0.0
    musc_prev = penult.get('MusculoEsqueleticoKG') or musc_val
    delta_musc = round(musc_val - musc_prev,
                       1) if len(df) > 1 and musc_val > 0 else 0.0
    c2.metric("Músculo Esquelético", f"{musc_val:.1f} kg" if musc_val >
              0 else "N/A", delta=f"{delta_musc:+.1f} kg" if musc_val > 0 else None)

    # Massa Gorda
    gorda_val = ult.get('MassaGordaKG') or 0.0
    gorda_prev = penult.get('MassaGordaKG') or gorda_val
    delta_gorda = round(gorda_val - gorda_prev,
                        1) if len(df) > 1 and gorda_val > 0 else 0.0
    c3.metric("Massa Gorda", f"{gorda_val:.1f} kg" if gorda_val > 0 else "N/A",
              delta=f"{delta_gorda:+.1f} kg" if gorda_val > 0 else None, delta_color="inverse")

    # Água Corporal e % de Hidratação
    agua_val = ult.get('AguaCorporalKG') or 0.0
    pct_agua = (agua_val / ult['PesoKG'] * 100) if agua_val > 0 else 0.0
    c4.metric("Água Corporal", f"{agua_val:.1f} kg" if agua_val >
              0 else "N/A", f"{pct_agua:.1f}% do Peso" if pct_agua > 0 else None)

    st.markdown("---")

    # --- 2. PAINEL DE COMPARATIVO TEMPORAL (DELTAS EM 7D, 30D E HISTÓRICO TOTAL) ---
    st.markdown(r"#### ⏱️ Comparativo Temporal de Progresso ($\Delta$ Deltas)")

    data_ult = ult['DataRegistro']
    df_7d = df[df['DataRegistro'] <= (data_ult - pd.Timedelta(days=7))]
    df_30d = df[df['DataRegistro'] <= (data_ult - pd.Timedelta(days=30))]
    ref_inicio = df.iloc[0]

    ref_7d = df_7d.iloc[-1] if not df_7d.empty else ref_inicio
    ref_30d = df_30d.iloc[-1] if not df_30d.empty else ref_inicio

    col_d1, col_d2, col_d3 = st.columns(3)

    with col_d1:
        st.markdown("**🗓️ Últimos 7 Dias**")
        d_p7 = ult['PesoKG'] - ref_7d['PesoKG']
        d_m7 = (ult.get('MusculoEsqueleticoKG') or 0) - \
            (ref_7d.get('MusculoEsqueleticoKG') or 0)
        d_g7 = (ult.get('MassaGordaKG') or 0) - \
            (ref_7d.get('MassaGordaKG') or 0)
        st.caption(f"• **Peso:** `{d_p7:+.1f} kg`")
        st.caption(f"• **Músculo:** `{d_m7:+.1f} kg`")
        st.caption(f"• **Gordura:** `{d_g7:+.1f} kg`")

    with col_d2:
        st.markdown("**📅 Últimos 30 Dias**")
        d_p30 = ult['PesoKG'] - ref_30d['PesoKG']
        d_m30 = (ult.get('MusculoEsqueleticoKG') or 0) - \
            (ref_30d.get('MusculoEsqueleticoKG') or 0)
        d_g30 = (ult.get('MassaGordaKG') or 0) - \
            (ref_30d.get('MassaGordaKG') or 0)
        st.caption(f"• **Peso:** `{d_p30:+.1f} kg`")
        st.caption(f"• **Músculo:** `{d_m30:+.1f} kg`")
        st.caption(f"• **Gordura:** `{d_g30:+.1f} kg`")

    with col_d3:
        st.markdown("**🏁 Histórico Total**")
        d_ptot = ult['PesoKG'] - ref_inicio['PesoKG']
        d_mtot = (ult.get('MusculoEsqueleticoKG') or 0) - \
            (ref_inicio.get('MusculoEsqueleticoKG') or 0)
        d_gtot = (ult.get('MassaGordaKG') or 0) - \
            (ref_inicio.get('MassaGordaKG') or 0)
        st.caption(f"• **Peso:** `{d_ptot:+.1f} kg`")
        st.caption(f"• **Músculo:** `{d_mtot:+.1f} kg`")
        st.caption(f"• **Gordura:** `{d_gtot:+.1f} kg`")

    st.markdown("---")

    # --- 3. INDICADORES DE QUALIDADE E SIMULADOR DE META ---
    st.markdown("#### 🎯 Indicadores Fisiológicos & Simulador de Meta")
    i1, i2, i3 = st.columns(3)

    altura_m = 1.78
    imc = ult['PesoKG'] / (altura_m ** 2)
    label_imc = "Abaixo" if imc < 18.5 else (
        "Ideal" if imc < 25 else ("Sobrepeso" if imc < 30 else "Obesidade"))
    i1.metric("IMC Estimado", f"{imc:.1f} kg/m²", label_imc)

    # Razão Músculo / Gordura
    razao_mg = (musc_val / gorda_val) if gorda_val > 0 else 0.0
    status_razao = "Excelente (>1.3)" if razao_mg >= 1.3 else (
        "Bom (>1.0)" if razao_mg >= 1.0 else "Aprimorar")
    i2.metric("Razão Músculo / Gordura", f"{razao_mg:.2f}", status_razao)

    # TMB
    tmb_val = int(ult.get('TMBKcal') or 0)
    i3.metric("Taxa Metabólica Basal (TMB)",
              f"{tmb_val} kcal" if tmb_val > 0 else "N/A", "Gasto em Repouso")

    # SIMULADOR DE SIMULAÇÃO DE GORDURA DESEJADA
    with st.expander("🧮 Simulador de Recomposição Corporal & Meta de Gordura"):
        st.caption(
            "Calcule quanto peso de gordura você precisa eliminar mantendo a massa magra intacta para atingir seu % de gordura alvo:")
        c_sim1, c_sim2 = st.columns(2)
        pct_atual = float(ult.get('PercentualGordura') or 25.0)
        meta_pct = c_sim1.slider(
            "Sua Meta de Gordura Corporal (%)", 8.0, 35.0, min(pct_atual, 18.0), step=0.5)

        massa_magra_atual = ult['PesoKG'] * (1 - (pct_atual / 100))
        peso_alvo = massa_magra_atual / (1 - (meta_pct / 100))
        gordura_a_perder = ult['PesoKG'] - peso_alvo

        if gordura_a_perder > 0:
            c_sim2.success(f"""
            🎯 **Para atingir {meta_pct:.1f}% de Gordura Corporal:**
            * **Peso Alvo Estimado:** `{peso_alvo:.1f} kg`
            * **Gordura a Eliminar:** `{gordura_a_perder:.1f} kg` *(mantendo {massa_magra_atual:.1f} kg de massa magra)*
            """)
        else:
            c_sim2.info(
                "Você já está na meta ou abaixo do percentual selecionado!")

    st.markdown("---")

    # --- 4. GRÁFICOS DE TENDÊNCIA TEMPORAL E MÉDIA MÓVEL DE 7 DIAS ---
    st.markdown("#### 📈 Evolução Temporal com Média Móvel (7 Dias)")

    df_grafico = df.set_index("DataRegistro").sort_index()

    # Cálculo da Média Móvel de 7 dias para eliminar flutuações de água/sódio
    df_grafico['Média Móvel Peso (7d)'] = df_grafico['PesoKG'].rolling(
        window=7, min_periods=1).mean()

    cols_exibir = ['PesoKG', 'Média Móvel Peso (7d)']
    if 'MusculoEsqueleticoKG' in df_grafico.columns and df_grafico['MusculoEsqueleticoKG'].notnull().any():
        cols_exibir.append('MusculoEsqueleticoKG')
    if 'MassaGordaKG' in df_grafico.columns and df_grafico['MassaGordaKG'].notnull().any():
        cols_exibir.append('MassaGordaKG')

    st.line_chart(df_grafico[cols_exibir])

    with st.expander("📋 Ver Histórico Completo de Bioimpedância em Tabela"):
        st.dataframe(df[["DataRegistro", "PesoKG", "PercentualGordura", "MusculoEsqueleticoKG", "MassaGordaKG",
                     "AguaCorporalKG", "TMBKcal"]].sort_values(by="DataRegistro", ascending=False), width="stretch")
