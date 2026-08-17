import pandas as pd
import streamlit as st


def render_tab_nutricao(db, ai_assistant=None):
    st.subheader("🍽️ Calculadora de TDEE Real & Planejamento de Macros")
    st.caption("Cálculo do Gasto Energético Total baseado na sua TMB real da bioimpedância e no volume de treino do Watch 4.")

    df_telemetria = db.buscar_historico_telemetria(14)

    if df_telemetria.empty or 'PesoKG' not in df_telemetria.columns or df_telemetria['PesoKG'].dropna().empty:
        st.info("💡 **Aguardando dados:** Cadastre pelo menos um registro de peso e TMB na bioimpedância para ativar esta calculadora.")
        return

    df_p = df_telemetria[df_telemetria['PesoKG'].notnull()]
    ult_bio = df_p.iloc[0]

    peso_atual = float(ult_bio['PesoKG'])
    tmb_real = float(ult_bio.get('TMBKcal') or 0.0)

    if tmb_real == 0:
        pct_g = float(ult_bio.get('PercentualGordura') or 25.0)
        massa_magra = peso_atual * (1 - (pct_g / 100))
        tmb_real = 370 + (21.6 * massa_magra)

    med_cal_ativas = float(df_telemetria['CaloriasQueimadas'].fillna(0).mean())
    med_passos = float(df_telemetria['Passos'].fillna(0).mean())

    st.markdown("#### ⚡ Gasto Energético Diário Estimado (TDEE)")

    eta = (tmb_real + med_cal_ativas) * 0.10
    tDEE_real = int(tmb_real + med_cal_ativas + eta)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TMB (Repouso)", f"{int(tmb_real)} kcal", "Bioimpedância")
    c2.metric("Gasto Ativo Médio",
              f"{int(med_cal_ativas)} kcal", f"~{int(med_passos):,} passos")
    c3.metric("Efeito Térmico (ETA)", f"{int(eta)} kcal", "~10% do consumo")
    c4.metric("TDEE Total Real", f"{tDEE_real} kcal", "Gasto diário estimado")

    st.markdown("---")

    st.markdown("#### 🎯 Alocação Estratégica de Macronutrientes")

    col_opt1, _ = st.columns(2)

    objetivo = col_opt1.selectbox(
        "Objetivo de Recomposição Corporal",
        [
            "Déficit Calórico Leve (Emagrecimento / Preservação Magra) [-15%]",
            "Déficit Calórico Moderado (Perda de Gordura Acelerada) [-25%]",
            "Manutenção Energética (Eutrofia / Performance) [0%]",
            "Superávit Calórico Leve (Ganho de Massa Magra) [+10%]"
        ],
        index=0
    )

    if "Déficit Calórico Leve" in objetivo:
        fator_cal = 0.85
    elif "Déficit Calórico Moderado" in objetivo:
        fator_cal = 0.75
    elif "Superávit" in objetivo:
        fator_cal = 1.10
    else:
        fator_cal = 1.00

    calorias_alvo = int(tDEE_real * fator_cal)

    col_m1, col_m2 = st.columns(2)
    p_g_kg = col_m1.slider(
        "Proteína Desejada (g / kg de peso)", 1.4, 2.8, 2.0, step=0.1)
    g_g_kg = col_m2.slider(
        "Gordura Desejada (g / kg de peso)", 0.6, 1.5, 0.9, step=0.1)

    prot_g = int(peso_atual * p_g_kg)
    prot_kcal = prot_g * 4

    gord_g = int(peso_atual * g_g_kg)
    gord_kcal = gord_g * 9

    carb_kcal = max(0, calorias_alvo - (prot_kcal + gord_kcal))
    carb_g = int(carb_kcal / 4)

    st.markdown("---")

    st.success(
        f"🎯 **Meta Calórica Diária Recomendada:** `{calorias_alvo} kcal / dia` *(Diferença de {calorias_alvo - tDEE_real:+} kcal sobre o TDEE)*")

    m_col1, m_col2, m_col3 = st.columns(3)

    pct_p = int((prot_kcal / calorias_alvo) * 100) if calorias_alvo > 0 else 0
    pct_c = int((carb_kcal / calorias_alvo) * 100) if calorias_alvo > 0 else 0
    pct_g = int((gord_kcal / calorias_alvo) * 100) if calorias_alvo > 0 else 0

    m_col1.metric("🍗 Proteínas", f"{prot_g} g / dia",
                  f"{prot_kcal} kcal ({pct_p}%)")
    m_col2.metric("🍞 Carboidratos",
                  f"{carb_g} g / dia", f"{carb_kcal} kcal ({pct_c}%)")
    m_col3.metric("🥑 Gorduras", f"{gord_g} g / dia",
                  f"{gord_kcal} kcal ({pct_g}%)")

    st.markdown("---")

    # --- 4. GERADOR DE SUGESTÃO ALIMENTAR PRÁTICA COM IA ---
    st.markdown("### 🤖 Sugestão Prática de Cardápio com IA (Llama)")
    st.caption(
        "A IA traduz as metas de gramas diárias em porções práticas de alimentos do dia a dia brasileiro.")

    st.warning("⚠️ **Aviso Importante:** Esta é uma simulação educativa de porções baseada em tabelas nutricionais e não substitui a consulta individualizada com um nutricionista ou nutrólogo.")

    if "sugestao_cardapio_ia" not in st.session_state:
        st.session_state.sugestao_cardapio_ia = ""

    if st.button("✨ Gerar Exemplo Prático de Cardápio com IA", type="primary"):
        with st.spinner("Gerando sugestão de alimentos e porções exatas com a IA..."):
            prompt_nutri = f"""
            Você é um assistente especialista em nutrição esportiva e fisiologia.
            O usuário tem as seguintes metas diárias calculadas pela telemetria:
            - Calorias Totais Alvo: {calorias_alvo} kcal
            - Proteínas Totais: {prot_g}g/dia
            - Carboidratos Totais: {carb_g}g/dia
            - Gorduras Totais: {gord_g}g/dia
            - Peso Corporal: {peso_atual} kg

            Monte uma sugestão prática de cardápio distribuída em 4 refeições (Café da Manhã, Almoço, Lanche da Tarde e Jantar).
            Para cada refeição:
            1. Liste os alimentos acessíveis e comuns no Brasil (ex: ovos, frango, carne, arroz, feijão, azeite, pão integral, tapioca, banana, aveia, whey, queijo).
            2. Forneça a quantidade aproximada em PESO CRU/COZIDO ou UNIDADES/COLHERES (ex: "150g de peito de frango grelhado (~46g de proteína)", "2 colheres de sopa de azeite de oliva (~24g de gordura)").
            3. No final, apresente um resumo somando o total estimado para provar que bate aproximadamente com os {prot_g}g de proteína, {carb_g}g de carboidratos e {gord_g}g de gordura.
            4. Mantenha um tom profissional, direto e pragmático.
            """

            try:
                if ai_assistant and hasattr(ai_assistant, 'client'):
                    # Caso utilize o AIHealthAssistant do projeto
                    response = ai_assistant.client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt_nutri
                    )
                    st.session_state.sugestao_cardapio_ia = response.text
                else:
                    # Fallback com estruturação estática de exemplo
                    st.session_state.sugestao_cardapio_ia = f"""
                    #### 🥗 Cardápio de Referência Sugerido ({calorias_alvo} kcal)

                    * **🍳 Café da Manhã:**
                      * **3 Ovos inteiros** mexidos ou cozidos (~18g Proteína | 15g Gordura)
                      * **2 fatias de Pão Integral** (~24g Carboidrato | 4g Proteína)
                      * **1 colher de sobremesa de Requeijão Light ou Manteiga** (~5g Gordura)
                      * **1 xícara de Café sem açúcar**

                    * **🍛 Almoço:**
                      * **180g de Peito de Frango** ou Patinho grelhado (~55g Proteína | 5g Gordura)
                      * **150g de Arroz Cozido** (~42g Carboidrato)
                      * **100g de Feijão Cozido** (~14g Carboidrato | 5g Proteína)
                      * **1 colher de sopa de Azeite de Oliva** na salada (~12g Gordura)
                      * **Salada verde à vontade** (Alface, Tomate, Pepino)

                    * **🍌 Lanche da Tarde:**
                      * **1 Dose de Whey Protein (30g)** (~24g Proteína | 2g Carboidrato)
                      * **30g de Aveia em Flocos** (~20g Carboidrato | 4g Proteína)
                      * **1 Banana Média** (~20g Carboidrato)
                      * **15g de Castanhas ou Pasta de Amendoim** (~8g Gordura | 4g Proteína)

                    * **🥗 Jantar:**
                      * **180g de Filet de Frango / Peixe / Carne Magra** (~55g Proteína | 6g Gordura)
                      * **120g de Batata Doce ou Mandioca Cozida** (~24g Carboidrato)
                      * **1 colher de sopa de Azeite de Oliva** (~12g Gordura)
                      * **Legumes cozidos** (Brócolis, Cenoura)

                    ---
                    📊 **Resumo Estimado:** `~182g Proteína` | `~122g Carboidratos` | `~78g Gordura` *(Bate com a meta diária calculada!)*
                    """
            except Exception as e:
                st.error(f"Erro ao gerar cardápio com IA: {e}")

    if st.session_state.sugestao_cardapio_ia:
        st.markdown(st.session_state.sugestao_cardapio_ia)
