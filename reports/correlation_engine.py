import sqlite3
import pandas as pd
import numpy as np

ARQUIVO_DB = "telemetria.db"


class CorrelationEngine:
    def __init__(self, db_path=ARQUIVO_DB):
        self.db_path = db_path

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def carregar_metas_usuario(self) -> dict:
        metas = {
            "meta_passos": 8000,
            "meta_sono_horas": 7.0,
            "meta_score_sono": 75,
            "limite_cafe_ml": 300,
            "meta_agua_auto": 1,
            "meta_agua_fixa_ml": 2500
        }
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chave, valor FROM metas_config")
                rows = cursor.fetchall()
                for k, v in rows:
                    if k in metas:
                        if k in ['meta_passos', 'meta_score_sono', 'limite_cafe_ml', 'meta_agua_fixa_ml', 'meta_agua_auto']:
                            metas[k] = int(float(v))
                        else:
                            metas[k] = float(v)
            return metas
        except Exception:
            return metas

    def preparar_dataframe_avancado(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Enriquece o DataFrame com variáveis fisiológicas derivadas e defasagens temporais (lag/lead)."""
        if df_raw.empty or len(df_raw) < 3:
            return pd.DataFrame()

        df = df_raw.sort_values(by="DataRegistro").copy()

        # 1. Variáveis Derivadas de Arquitetura do Sono
        df['TempoSonoMinutos'] = df['HorasSono'].fillna(0) * 60
        df['PctSonoProfundo'] = np.where(df['TempoSonoMinutos'] > 0, (
            df['SonoProfundoMinutos'].fillna(0) / df['TempoSonoMinutos']) * 100, 0)
        df['PctSonoREM'] = np.where(df['TempoSonoMinutos'] > 0, (df['SonoREMMinutos'].fillna(
            0) / df['TempoSonoMinutos']) * 100, 0)
        df['RazaoProfundoREM'] = np.where(
            df['SonoREMMinutos'] > 0, df['SonoProfundoMinutos'].fillna(0) / df['SonoREMMinutos'], 0)

        # 2. Dados de Saúde Mental (Cruzamento por Data)
        try:
            with self._get_connection() as conn:
                df_mental = pd.read_sql_query(
                    "SELECT data_registro as DataRegistro, humor_score as HumorScore, minutos_descompressao as MinutosDescompressao FROM SaudeMentalLogs", conn)
            if not df_mental.empty:
                df = pd.merge(df, df_mental, on="DataRegistro", how="left")
        except Exception:
            pass

        # 3. Métrica de Descompressão Parassimpática e Hidratação Real
        if 'MinutosDescompressao' not in df.columns:
            df['MinutosDescompressao'] = 0
        if 'HumorScore' not in df.columns:
            df['HumorScore'] = 5

        # 4. Defasagem Temporal (Efeito do hábito de hoje no dia seguinte - Shift)
        df['ReadinessDiaSeguinte'] = df['ScoreProntitudade'].shift(-1)
        df['FCRepousoDiaSeguinte'] = df['FrequenciaCardiacaRepouso'].shift(-1)
        df['DisposicaoDiaSeguinte'] = df['DisposicaoAcordarScore'].shift(-1)

        return df

    def calcular_matriz_correlacao(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """Calcula a Matriz de Pearson com variáveis expandidas de hábitos e fisiologia."""
        df = self.preparar_dataframe_avancado(df_raw)
        if df.empty:
            return pd.DataFrame()

        colunas_analise = {
            "Passos": "Passos",
            "HorasSono": "Horas Sono",
            "QualidadeSonoScore": "Score Sono",
            "SonoProfundoMinutos": "Sono Profundo (m)",
            "SonoREMMinutos": "Sono REM (m)",
            "PctSonoProfundo": "% Profundo",
            "PctSonoREM": "% REM",
            "FrequenciaCardiacaRepouso": "FC Repouso",
            "SpO2MedioPct": "SpO₂ Noturno",
            "ConsumoAguaML": "Água (ml)",
            "ConsumoCafeML": "Cafeína (ml)",
            "ConsumoCafeinaMG": "Cafeína (mg)",
            "NivelEstresseScore": "Estresse",
            "DisposicaoAcordarScore": "Disposição",
            "FocoClarezaScore": "Foco Mental",
            "DorMuscularScore": "Dor Muscular (DOMS)",
            "MinutosDescompressao": "Descompressão (m)",
            "HumorScore": "Humor",
            "ScoreProntitudade": "Readiness"
        }

        cols_existentes = [
            c for c in colunas_analise.keys() if c in df.columns]
        df_sub = df[cols_existentes].dropna(
            thresh=int(len(cols_existentes) * 0.5))

        if len(df_sub) < 3:
            return pd.DataFrame()

        matriz = df_sub.corr(method="pearson").round(2)
        matriz.rename(columns=colunas_analise,
                      index=colunas_analise, inplace=True)
        return matriz

    def gerar_insights_correlacao(self, df_raw: pd.DataFrame) -> list[str]:
        """Gera cartões de análise e recomendações baseadas nos coeficientes significativos de Pearson."""
        df = self.preparar_dataframe_avancado(df_raw)
        if df.empty or len(df) < 4:
            return ["ℹ️ **Histórico em construção:** Registre ao menos 4 a 7 dias para desbloquear os padrões de correlação."]

        matriz = df.corr(numeric_only=True)
        insights = []

        # 1. Cafeína x Sono REM / Latência
        if 'ConsumoCafeML' in matriz.columns and 'SonoREMMinutos' in matriz.columns:
            r_cafe_rem = matriz.loc['ConsumoCafeML', 'SonoREMMinutos']
            if not np.isnan(r_cafe_rem) and abs(r_cafe_rem) >= 0.35:
                if r_cafe_rem < 0:
                    insights.append(
                        f"☕ **Padrão de Cafeína x Sono REM (r = {r_cafe_rem:.2f}):** Detectamos uma correlação negativa expressiva. O aumento do consumo de café/estimulantes reduz diretamente seus minutos de Sono REM. Experimente antecipar a última dose para antes das 14:00.")
                else:
                    insights.append(
                        f"☕ **Cafeína & Sono REM (r = {r_cafe_rem:.2f}):** O consumo atual de estimulantes não está comprometendo o seu sono restaurador cognitivo.")

        # 2. Descompressão (Hobbies/Oficina) x Readiness / Estresse
        if 'MinutosDescompressao' in matriz.columns and 'ReadinessDiaSeguinte' in matriz.columns:
            r_desc_read = matriz.loc['MinutosDescompressao',
                                     'ReadinessDiaSeguinte']
            if not np.isnan(r_desc_read) and r_desc_read >= 0.35:
                insights.append(
                    f"🌿 **Impacto do Foco Prático (r = +{r_desc_read:.2f}):** Nos dias em que você dedica tempo à descompressão manual (marcenaria, bonsai, projetos 3D), seu Readiness no dia seguinte apresenta uma elevação direta!")

        # 3. Hidratação x Foco Mental & Dores Musculares
        if 'ConsumoAguaML' in matriz.columns and 'FocoClarezaScore' in matriz.columns:
            r_agua_foco = matriz.loc['ConsumoAguaML', 'FocoClarezaScore']
            if not np.isnan(r_agua_foco) and r_agua_foco >= 0.40:
                insights.append(
                    f"💧 **Hidratação & Clareza Mental (r = +{r_agua_foco:.2f}):** Forte correlação positiva! O cumprimento da meta hídrica está diretamente associado a maior nível de foco e menor sensação de névoa mental.")

        # 4. FC de Repouso x Estresse / Prontidão
        if 'FrequenciaCardiacaRepouso' in matriz.columns and 'NivelEstresseScore' in matriz.columns:
            r_fc_estresse = matriz.loc['FrequenciaCardiacaRepouso',
                                       'NivelEstresseScore']
            if not np.isnan(r_fc_estresse) and r_fc_estresse >= 0.40:
                insights.append(
                    f"🫀 **Carga Alostática x Coração (r = +{r_fc_estresse:.2f}):** O aumento no seu nível de estresse percebido eleva a sua frequência cardíaca de repouso noturna. Recomenda-se higiene do sono parassimpática antes de deitar.")

        # 5. Sono Profundo x Disposição ao Acordar
        if 'SonoProfundoMinutos' in matriz.columns and 'DisposicaoAcordarScore' in matriz.columns:
            r_prof_disp = matriz.loc['SonoProfundoMinutos',
                                     'DisposicaoAcordarScore']
            if not np.isnan(r_prof_disp) and r_prof_disp >= 0.35:
                insights.append(
                    f"😴 **Recuperação Física Profunda (r = +{r_prof_disp:.2f}):** Seu nível de disposição matinal é fortemente dependente dos minutos de Sono Profundo do Galaxy Watch 4.")

        if not insights:
            insights.append(
                "📊 **Padrões Estáveis:** Suas métricas de sono, hábitos e fisiologia estão equilibradas sem flutuações extremas nos últimos dias.")

        return insights

    def detectar_alertas_fadiga_snc(self, df_raw: pd.DataFrame) -> list[dict]:
        """Identifica sinais fisiológicos de sobrecarga/overtraining no Sistema Nervoso Central."""
        alertas = []
        if df_raw.empty or len(df_raw) < 3:
            return alertas

        df = df_raw.head(3)
        readiness_med = df['ScoreProntitudade'].fillna(75).mean()
        fc_med = df['FrequenciaCardiacaRepouso'].fillna(65).mean()
        estresse_med = df['NivelEstresseScore'].fillna(35).mean()
        dor_med = df['DorMuscularScore'].fillna(
            0).mean() if 'DorMuscularScore' in df.columns else 0

        if readiness_med < 60 and dor_med > 5:
            alertas.append({
                "nivel": "danger",
                "titulo": "🚨 Alerta de Fadiga do SNC & Acúmulo de Carga",
                "msg": f"Sua prontidão média dos últimos 3 dias caiu para **{readiness_med:.0f}/100** com dores musculares elevadas (**{dor_med:.1f}/10**). Recomendamos priorizar treinos de recuperação ativa ou mobilidade leve hoje."
            })
        elif fc_med > 75 and estresse_med > 50:
            alertas.append({
                "nivel": "warning",
                "titulo": "⚠️ Elevação de Tônus Simpático Noturno",
                "msg": f"Sua FC de repouso média está elevada (**{fc_med:.0f} BPM**) acompanhada de estresse percebido alto (**{estresse_med:.0f}/100**). Evite treinos exaustivos à noite e reduza estimulantes."
            })

        return alertas

    def buscar_resumo_suplementacao(self, dias=30) -> pd.DataFrame:
        try:
            with self._get_connection() as conn:
                query = f"""
                    SELECT s.nome, s.dose, s.horario, s.categoria_acao,
                           COUNT(l.id) as dias_tomados,
                           ROUND((CAST(COUNT(l.id) AS REAL) / {dias}) * 100, 1) as taxa_adesao
                    FROM suplementos_custom s
                    LEFT JOIN SuplementosLogs l ON s.id = l.suplemento_id AND l.tomado = 1
                    WHERE s.ativo = 1
                    GROUP BY s.id
                    ORDER BY taxa_adesao DESC
                """
                return pd.read_sql_query(query, conn)
        except Exception:
            return pd.DataFrame()
