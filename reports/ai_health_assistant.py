import sqlite3
import json
import pandas as pd
from datetime import datetime
import requests
import unicodedata

ARQUIVO_DB = "telemetria.db"


def remover_acentos_e_cedilha(texto: str) -> str:
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', texto)
    return "".join(c for c in texto_norm if unicodedata.category(c) != 'Mn').lower()


class AIHealthAssistant:
    def __init__(self, ollama_url="http://localhost:11434/api/generate", model_name="llama3"):
        self.ollama_url = ollama_url
        self.model_name = model_name

    def _buscar_dados_completos(self) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        try:
            conn = sqlite3.connect(ARQUIVO_DB)
            df_tel = pd.read_sql_query(
                "SELECT * FROM QualidadeVida ORDER BY DataRegistro DESC LIMIT 30", conn)
            df_ex = pd.read_sql_query(
                "SELECT * FROM ExamesLaboratoriais ORDER BY data_exame DESC", conn)
            df_sup = pd.read_sql_query("""
                SELECT s.nome, s.dose, s.horario, s.categoria_acao, s.mecanismo, COUNT(l.id) as dias_tomados
                FROM suplementos_custom s
                LEFT JOIN SuplementosLogs l ON s.id = l.suplemento_id AND l.tomado = 1
                GROUP BY s.id
            """, conn)
            try:
                df_mental = pd.read_sql_query(
                    "SELECT * FROM SaudeMentalLogs ORDER BY data_registro DESC LIMIT 30", conn)
            except Exception:
                df_mental = pd.DataFrame()
            conn.close()
            return df_tel, df_ex, df_sup, df_mental
        except Exception:
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def _buscar_ultimos_treinos(self, limite=7) -> list[dict]:
        try:
            conn = sqlite3.connect(ARQUIVO_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM SessoesTreino ORDER BY data_registro DESC LIMIT {limite}")
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _buscar_historico_chat_terapeutico(self, data_str: str) -> list[dict]:
        """Recupera as mensagens trocadas na sessão terapêutica do dia no banco."""
        try:
            conn = sqlite3.connect(ARQUIVO_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                "SELECT origem, mensagem FROM SessaoTerapeuticaChat WHERE data_registro = ? ORDER BY id ASC", (data_str,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def _salvar_mensagem_chat_terapeutico(self, data_str: str, origem: str, mensagem: str):
        """Grava uma mensagem do chat terapêutico no banco de dados SQLite."""
        try:
            conn = sqlite3.connect(ARQUIVO_DB)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO SessaoTerapeuticaChat (data_registro, origem, mensagem)
                VALUES (?, ?, ?)
            ''', (data_str, origem, mensagem))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def responder_chat_terapeutico(self, data_str: str, mensagem_usuario: str) -> str:
        """Processa a mensagem do usuário no chat terapêutico com contexto completo e salva no banco."""
        self._salvar_mensagem_chat_terapeutico(
            data_str, "usuario", mensagem_usuario)

        df_tel, df_ex, df_sup, df_mental = self._buscar_dados_completos()
        historico_chat = self._buscar_historico_chat_terapeutico(data_str)

        m_hoje = df_mental[df_mental['data_registro'] ==
                           data_str] if not df_mental.empty else pd.DataFrame()
        m = m_hoje.iloc[0] if not m_hoje.empty else {}

        u_hoje = df_tel[df_tel['DataRegistro'] ==
                        data_str] if not df_tel.empty else pd.DataFrame()
        u = u_hoje.iloc[0] if not u_hoje.empty else {}

        dialogo_anterior_str = "\n".join([
            f"{'Usuário' if msg['origem'] == 'usuario' else 'Terapeuta'}: {msg['mensagem']}"
            for msg in historico_chat[:-1]
        ]) if len(historico_chat) > 1 else "Início da conversa após parecer inicial."

        prompt_chat_terapeuta = f"""
Você é uma Psicóloga e Terapeuta Cognitivo-Comportamental (TCC) empática, sábia, acolhedora e pragmática.
Você está conversando no chat contínuo com o usuário sobre o dia {data_str}.

CONTEXTO EMOCIONAL & FISIOLÓGICO DE HOJE:
- Humor: {m.get('humor_score', 5)}/10 ({m.get('estado_emocional', 'Neutro')}) | Gatilhos: {m.get('gatilhos', 'Nenhum')}
- Descompressão: {m.get('minutos_descompressao', 0)} min ({m.get('atividade_descompressao', 'Nenhuma')})
- Preocupação TCC: "{m.get('diario_tcc_pensamento', 'Nenhum')}" | Reenquadramento: "{m.get('diario_tcc_reenquadramento', 'Nenhum')}"
- Readiness: {u.get('ScoreProntitudade', 75)}/100 | Sono: {u.get('HorasSono', 0)}h

HISTÓRICO DA CONVERSA DE HOJE:
{dialogo_anterior_str}

MENSAGEM ATUAL DO USUÁRIO:
"{mensagem_usuario}"

Instruções: Responda de forma acolhedora, reflexiva, curta (2 a 4 parágrafos) e focada no reencaminhamento cognitivo das preocupações trazidas pelo usuário.
"""

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt_chat_terapeuta,
                "stream": False,
                "keep_alive": "24h"
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=120)
            if resp.status_code == 200:
                resposta_ia = resp.json().get("response", "").strip()
                if resposta_ia:
                    self._salvar_mensagem_chat_terapeutico(
                        data_str, "terapeuta", resposta_ia)
                    return resposta_ia
        except Exception as e:
            return f"⚠️ **Erro ao conectar com o terapeuta virtual:** `{e}`."

        return "⚠️ Não foi possível obter resposta no momento."

    def gerar_parecer_terapeutico(self, data_str: str) -> str:
        """Gera uma análise psicológica acolhedora no formato de sessão TCC/Mindfulness via Llama 3."""
        df_tel, df_ex, df_sup, df_mental = self._buscar_dados_completos()

        if df_mental.empty:
            return "⚠️ **Nenhum registro de saúde mental encontrado.** Preencha os campos da aba '🧠 Saúde Mental' hoje para iniciar a análise acolhedora."

        m_hoje = df_mental[df_mental['data_registro'] == data_str]
        m = m_hoje.iloc[0] if not m_hoje.empty else df_mental.iloc[0]

        u_hoje = df_tel[df_tel['DataRegistro'] ==
                        data_str] if not df_tel.empty else pd.DataFrame()
        u = u_hoje.iloc[0] if not u_hoje.empty else (
            df_tel.iloc[0] if not df_tel.empty else {})

        humor_score = m.get('humor_score', 5)
        estado_emo = m.get('estado_emocional', 'Neutro')
        gatilhos = m.get('gatilhos', 'Nenhum informado')
        min_desc = m.get('minutos_descompressao', 0)
        ativ_desc = m.get('atividade_descompressao', 'Nenhuma')
        pensamento = m.get('diario_tcc_pensamento', 'Nenhum registrado')
        reenquadramento = m.get(
            'diario_tcc_reenquadramento', 'Nenhum registrado')

        sono_h = u.get('HorasSono', 0)
        readiness = u.get('ScoreProntitudade', 75)
        estresse = u.get('NivelEstresseScore', 0)

        prompt_terapeuta = f"""
Você é uma Psicóloga e Terapeuta Cognitivo-Comportamental (TCC) empática, sábia, pragmática e especialista em Medicina Mente-Corpo e Regulação do Sistema Nervoso.

Realize um Acolhimento Terapêutico e crie um Parecer Reflexivo para o usuário sobre o dia de HOJE ({data_str}).

DADOS EMOCIONAIS E COGNITIVOS DE HOJE ({data_str}):
- Escala de Humor: {humor_score}/10
- Estado Predominante: {estado_emo}
- Gatilhos e Estressores do Dia: {gatilhos}
- Tempo de Descompressão (Hobbies/Oficina/Bonsai): {min_desc} min em "{ativ_desc}"
- Registro TCC - Pensamento Intrusivo ("E se...?"): "{pensamento}"
- Registro TCC - Reenquadramento Racional: "{reenquadramento}"

DADOS DE RECOMPOSIÇÃO E FISIOLOGIA (WATCH 4):
- Sono da Noite Anterior: {sono_h}h | Readiness Score: {readiness}/100 | Nível de Estresse Percebido: {estresse}/100

---

ESTRUTURA OBRIGATÓRIA DA RESPOSTA TERAPÊUTICA:

### 🧘 1. Espaço de Acolhimento & Escuta Empática
Valide os sentimentos do usuário de forma humana, sem julgamentos. Comente sobre o humor ({humor_score}/10) e a carga emocional trazida pelos gatilhos ({gatilhos}).

### 🧠 2. Análise Cognitiva (Identificação de Padrões e Distorções)
Examine o pensamento intrusivo registrado ("{pensamento}"). Identifique se há distorções cognitivas (como Catastrofização, Leitura de Mente ou Pensamento Tudo-ou-Nada). Avalie a eficácia do reenquadramento racional feito pelo usuário ("{reenquadramento}").

### 🌿 3. O Papel da Descompressão no Sistema Nervoso Autônomo
Comente sobre os {min_desc} minutos dedicados à atividade de descompressão ({ativ_desc}). Explique como a ativação das mãos e do foco prático (marcenaria, bonsai, projetos 3D) desliga o modo "Luta ou Fuga" e estimula o tónus vagal (parassimpático).

### 💡 4. Prescrição Terapêutica & Âncora para a Noite
Forneça de 2 a 3 orientações curtas de higienização mental para a noite, garantindo que as preocupações do trabalho não invadam o sono REM.

Aviso final amigável: Lembre suavemente que este parecer é um exercício guiado de auto-reflexão via IA e não substitui o acompanhamento psicológico profissional.
"""

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt_terapeuta,
                "stream": False,
                "keep_alive": "24h"
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=300)
            if resp.status_code == 200:
                res_txt = resp.json().get("response", "").strip()
                if len(res_txt) > 100:
                    self._salvar_mensagem_chat_terapeutico(
                        data_str, "terapeuta", res_txt)
                    return res_txt
        except Exception as e:
            return f"⚠️ **Erro na consulta terapêutica:** `{e}`. Verifique se o serviço do Ollama está ativo."

        return "⚠️ Não foi possível gerar a análise terapêutica no momento."

    def prescrever_treino_diario(self, data_str: str) -> dict:
        df_tel, df_ex, df_sup, df_mental = self._buscar_dados_completos()
        ultimos_treinos = self._buscar_ultimos_treinos(5)

        if df_tel.empty:
            return {}

        u_hoje = df_tel[df_tel['DataRegistro'] == data_str]
        u = u_hoje.iloc[0] if not u_hoje.empty else df_tel.iloc[0]

        readiness = int(u.get('ScoreProntitudade', 75) or 75)
        disposicao = int(u.get('DisposicaoAcordarScore', 5) or 5)
        dor_doms = int(u.get('DorMuscularScore', 0) or 0)
        sono_profundo = int(u.get('SonoProfundoMinutos', 60) or 60)
        sono_rem = int(u.get('SonoREMMinutos', 90) or 90)

        humor_txt = "Neutro"
        min_descompressao = 0
        if not df_mental.empty:
            m_hoje = df_mental[df_mental['data_registro'] == data_str]
            if not m_hoje.empty:
                m_row = m_hoje.iloc[0]
                humor_txt = m_row.get('estado_emocional', 'Neutro')
                min_descompressao = int(
                    m_row.get('minutos_descompressao', 0) or 0)

        historico_treinos_str = "\n".join([
            f"- {t['data_registro']}: {t['modalidade']} ({t['duracao_minutos']} min, PSE: {t.get('sensacao_pos_treino', 5)}/10) - Notas: {t.get('notas_treino', '')}"
            for t in ultimos_treinos
        ]) if ultimos_treinos else "Nenhum treino recente registrado."

        prompt_prescricao = f"""
Você é um Treinador de Alta Performance e Fisiologista do Esporte.
Com base nos dados reais de recuperação e saúde mental de HOJE ({data_str}), prescreva o treino ideal.

DADOS DE RECUPERAÇÃO & SAÚDE MENTAL DE HOJE:
- Readiness Score: {readiness}/100
- Disposição ao Acordar: {disposicao}/10 | Estado Emocional: {humor_txt}
- Dor Muscular / DOMS Atual: {dor_doms}/10 | Minutos de Descompressão: {min_descompressao} min
- Sono Profundo da Noite: {sono_profundo} min | Sono REM: {sono_rem} min

HISTÓRICO RECENTE DE TREINOS:
{historico_treinos_str}

REGRAS DE PRESCRIÇÃO FISIOLÓGICA:
1. Se o Readiness < 65, Disposição < 5, Estado Emocional "Exaurido/Ansioso" ou Dor MUSCULAR > 6: Prescreva treino leve de Recuperação Ativa, Caminhada ou Mobilidade.
2. Se o Readiness >= 80 e Dor Muscular < 3: Prescreva treino intenso (Hipertrofia, Musculação com Carga ou Corrida).
3. Para Caminhada/Corrida/Ciclismo, CALCULE A DISTÂNCIA E O PACE CORRETOS com base no tempo e velocidade. (Ex: 30 min de Caminhada Leve a 3 km/h = Distância de 1.5 km e Pace de "20:00").
4. A FC máxima deve ser coerente com a FC média (FC Máx = FC Média + 15 a 25 BPM).

Retorne estritamente um JSON com estas chaves exatas:
"nome_sugerido" (string), "modalidade" (string), "duracao_min" (integer), "calorias_kcal" (integer), "bpm_alvo" (integer), "bpm_max" (integer), "distancia_km" (float), "pace_medio" (string ex: "20:00"), "pse_alvo" (integer), "exercicios" (string contendo a lista de exercicios)
"""

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt_prescricao,
                "format": "json",
                "stream": False,
                "keep_alive": "24h"
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=120)
            if resp.status_code == 200:
                raw_txt = resp.json().get("response", "").strip()
                res_dict = json.loads(raw_txt)
                if isinstance(res_dict, dict) and "nome_sugerido" in res_dict:
                    return res_dict
        except Exception:
            pass

        e_caminhada = readiness < 65 or disposicao < 5 or dor_doms > 5
        dur_min = 30 if e_caminhada else 45
        dist_km = round((3.0 * (dur_min / 60)), 2) if e_caminhada else 0.0
        pace_str = "20:00" if e_caminhada else ""
        bpm_med = 100 if e_caminhada else 125
        bpm_m = bpm_med + 15 if e_caminhada else bpm_med + 25

        return {
            "nome_sugerido": f"Caminhada Leve de Recuperação ({dur_min} min)" if e_caminhada else f"Treino de Musculação Adaptado ({dur_min} min)",
            "modalidade": "Caminhada" if e_caminhada else "Musculação",
            "duracao_min": dur_min,
            "calorias_kcal": 110 if e_caminhada else 280,
            "bpm_alvo": bpm_med,
            "bpm_max": bpm_m,
            "distancia_km": dist_km,
            "pace_medio": pace_str,
            "pse_alvo": 3 if e_caminhada else 6,
            "exercicios": f"Caminhada leve em ritmo de 3 km/h por {dur_min} minutos sem carga adicional para descompressão muscular." if e_caminhada else "- Supino Reto (3x10)\n- Puxada Frontal (3x12)\n- Leg Press (3x12)\n- Elevação Lateral (3x15)"
        }

    def _construir_prompt_contextual(self, df_tel: pd.DataFrame, df_ex: pd.DataFrame, df_sup: pd.DataFrame, df_mental: pd.DataFrame) -> str:
        df_7 = df_tel.head(7) if not df_tel.empty else pd.DataFrame()
        u_hoje = df_tel.iloc[0] if not df_tel.empty else {}

        resumo_7d = {
            "passos_med": int(df_7['Passos'].fillna(0).mean()) if not df_7.empty and 'Passos' in df_7.columns else 0,
            "sono_horas_med": round(df_7['HorasSono'].fillna(0).mean(), 1) if not df_7.empty and 'HorasSono' in df_7.columns else 0.0,
            "sono_score_med": int(df_7['QualidadeSonoScore'].fillna(0).mean()) if not df_7.empty and 'QualidadeSonoScore' in df_7.columns else 0,
            "sono_profundo_med": int(df_7['SonoProfundoMinutos'].fillna(0).mean()) if not df_7.empty and 'SonoProfundoMinutos' in df_7.columns else 0,
            "sono_rem_med": int(df_7['SonoREMMinutos'].fillna(0).mean()) if not df_7.empty and 'SonoREMMinutos' in df_7.columns else 0,
            "spo2_med": round(df_7['SpO2MedioPct'].fillna(97.2).mean(), 1) if not df_7.empty and 'SpO2MedioPct' in df_7.columns else 97.2,
            "fc_repouso_med": int(df_7['FrequenciaCardiacaRepouso'].fillna(68).mean()) if not df_7.empty and 'FrequenciaCardiacaRepouso' in df_7.columns else 68,
            "readiness_med": int(df_7['ScoreProntitudade'].fillna(75).mean()) if not df_7.empty and 'ScoreProntitudade' in df_7.columns else 75,
            "estresse_med": int(df_7['NivelEstresseScore'].fillna(0).mean()) if not df_7.empty and 'NivelEstresseScore' in df_7.columns else 0,
            "peso_kg": float(df_tel['PesoKG'].dropna().iloc[0]) if not df_tel.empty and not df_tel['PesoKG'].dropna().empty else 90.0
        }

        m_hoje = df_mental.iloc[0] if not df_mental.empty else {}
        humor_hoje = m_hoje.get('estado_emocional', 'Não informado')
        score_humor = m_hoje.get('humor_score', 'N/A')
        gatilhos_hoje = m_hoje.get('gatilhos', 'Nenhum')
        min_desc = m_hoje.get('minutos_descompressao', 0)

        hoje_data = u_hoje.get('DataRegistro', 'Hoje')
        hoje_sono_tot = u_hoje.get('HorasSono', 0.0) or 0.0
        hoje_profundo = int(u_hoje.get('SonoProfundoMinutos', 0) or 0)
        hoje_rem = int(u_hoje.get('SonoREMMinutos', 0) or 0)
        hoje_readiness = int(u_hoje.get('ScoreProntitudade', 75) or 75)
        hoje_disposicao = u_hoje.get('DisposicaoAcordarScore', 5) or 5

        suplementos_lista = []
        if not df_sup.empty:
            for _, s in df_sup.iterrows():
                mec = s.get('mecanismo') or "Ação contínua"
                suplementos_lista.append(
                    f"{s['nome']} ({s['dose']} - {s['horario']}) [Classe: {s.get('categoria_acao', 'Geral')}] -> Mecanismo: {mec}")

        exames_lista = []
        if not df_ex.empty:
            ult_data = df_ex['data_exame'].iloc[0]
            df_ult = df_ex[df_ex['data_exame'] == ult_data]
            for _, r in df_ult.iterrows():
                status_str = "Normal"
                if pd.notnull(r['referencia_max']) and r['resultado'] > r['referencia_max']:
                    status_str = f"ELEVADO (Max: {r['referencia_max']})"
                elif pd.notnull(r['referencia_min']) and r['resultado'] < r['referencia_min']:
                    status_str = f"ABAIXO (Min: {r['referencia_min']})"
                exames_lista.append(
                    f"{r['marcador']}: {r['resultado']} {r['unidade']} [{status_str}]")

        prompt = f"""
Você é um Médico Fisiologista do Esporte e Especialista em Medicina do Estilo de Vida e Neurologia do Sono.

Analise minuciosamente os dados abaixo do usuário, DESTACANDO A RECUPERAÇÃO FISIOLÓGICA E O ESTADO MENTAL DE HOJE ({hoje_data}) e comparando-os com as médias semanais.

### 🧠 ESTADO EMOCIONAL & SAÚDE MENTAL DE HOJE:
- **Estado de Humor:** {humor_hoje} (Score: {score_humor}/10)
- **Gatilhos Identificados:** {gatilhos_hoje}
- **Tempo de Descompressão Parassimpática (Hobbies/Marcenaria/Bonsai):** {min_desc} min

### ⌚ FISIOLOGIA DO SONO DA ÚLTIMA NOITE (Registro em {hoje_data}):
- **Duração do Sono:** {hoje_sono_tot}h | **Readiness Score:** {hoje_readiness}/100
- **Sono Profundo:** {hoje_profundo} min | **Sono REM:** {hoje_rem} min | **Disposição:** {hoje_disposicao}/10

### 📈 TENDÊNCIA E MÉDIAS DOS ÚLTIMOS 7 DIAS:
- **Média de Sono Total:** {resumo_7d['sono_horas_med']}h/noite | **Score de Sono:** {resumo_7d['sono_score_med']}/100
- **Estresse Acumulado:** {resumo_7d['estresse_med']}/100 | **FC Repouso:** {resumo_7d['fc_repouso_med']} BPM
- **Protocolo de Suplementos Ativo:** {suplementos_lista if suplementos_lista else 'Nenhum ativo'}
- **Marcadores Laboratoriais Recentes:** {exames_lista if exames_lista else 'Nenhum exame'}

---

### ESTRUTURA OBRIGATÓRIA DA SUA RESPOSTA:

#### 1. 🩺 Diagnóstico Holístico da Arquitetura do Sono & Fisiologia
Avalie o **Sono Profundo ({hoje_profundo} min)** e **Sono REM ({hoje_rem} min)** da ÚLTIMA NOITE ({hoje_data}) cruzando com o **Estado Emocional ({humor_hoje})** e os **Minutos de Descompressão ({min_desc} min)**.

#### 2. 🧠 Avaliação da Carga Alostática & Regulação do Sistema Nervoso
Analise o impacto dos gatilhos citados ({gatilhos_hoje}) no cortisol e na recuperação noturna. Recomende estratégias de TCC ou descompressão manual (oficina, bonsai, projetos 3D) para reduzir a reatividade simpática.

#### 3. 💊 Impacto Farmacológico do Protocolo (Medicamentos & Suplementação)
Comente sobre suplementos indutores de relaxamento ou moduladores de neurotransmissores (como Magnésio/Inositol) e o impacto no sono REM.

#### 4. 🥗 Prescrição Nutricional & Janela Alimentar
Meta proteica (1.8g a 2.0g/kg para {resumo_7d['peso_kg']}kg) e corte rígido de estimulantes.

#### 5. 🏋️ Prescrição de Exercícios & Recuperação
Ajustes do treino do dia alinhados ao estado mental e nível de estresse.

#### 6. 🎯 Plano Tático Semanal (3 a 5 Metas Claras)
Metas objetivas e quantificáveis.
"""
        return prompt

    def gerar_parecer(self) -> str:
        df_tel, df_ex, df_sup, df_mental = self._buscar_dados_completos()

        if df_tel.empty:
            return "⚠️ **Dados insuficientes no histórico** para gerar um parecer preditivo. Registre pelo menos 3 a 7 dias de telemetria."

        prompt = self._construir_prompt_contextual(
            df_tel, df_ex, df_sup, df_mental)

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "24h"
            }
            response = requests.post(
                self.ollama_url, json=payload, timeout=300)
            if response.status_code == 200:
                res_text = response.json().get("response", "").strip()
                if len(res_text) > 200:
                    return res_text
        except requests.exceptions.ConnectionError:
            return f"⚠️ **Servidor Ollama Indisponível:** Não foi possível conectar a `{self.ollama_url}`."
        except requests.exceptions.Timeout:
            return "⏳ **Tempo de resposta esgotado:** O modelo local demorou mais de 5 minutos para gerar o parecer completo."
        except Exception as err:
            return f"⚠️ **Erro na resposta da IA local (Ollama):** `{err}`."

        return "⚠️ O Llama 3 local não retornou uma resposta válida dentro do tempo esperado."

    def responder_chat_telemetria(self, pergunta_usuario: str) -> str:
        df_tel, df_ex, df_sup, df_mental = self._buscar_dados_completos()

        if df_tel.empty and df_ex.empty:
            return "Não encontrei dados suficientes no banco para responder à sua pergunta."

        df_7 = df_tel.head(7) if not df_tel.empty else pd.DataFrame()
        u_hoje = df_tel.iloc[0] if not df_tel.empty else {}
        m_hoje = df_mental.iloc[0] if not df_mental.empty else {}

        resumo_ctx = {
            "hoje_data": u_hoje.get('DataRegistro', 'Hoje'),
            "hoje_sono_tot": u_hoje.get('HorasSono', 0.0) or 0.0,
            "hoje_profundo": int(u_hoje.get('SonoProfundoMinutos', 0) or 0),
            "hoje_rem": int(u_hoje.get('SonoREMMinutos', 0) or 0),
            "hoje_readiness": int(u_hoje.get('ScoreProntitudade', 75) or 75),
            "hoje_disposicao": u_hoje.get('DisposicaoAcordarScore', 5) or 5,
            "humor_hoje": m_hoje.get('estado_emocional', 'Não informado'),
            "gatilhos_hoje": m_hoje.get('gatilhos', 'Nenhum'),
            "min_desc": m_hoje.get('minutos_descompressao', 0),
            "readiness": int(df_7['ScoreProntitudade'].fillna(75).mean()) if not df_7.empty and 'ScoreProntitudade' in df_7.columns else 75,
            "peso_kg": float(df_tel['PesoKG'].dropna().iloc[0]) if not df_tel.empty and not df_tel['PesoKG'].dropna().empty else 90.0
        }

        prompt_chat = f"""
Você é o assistente virtual médico e de alta performance especialista no histórico de saúde do usuário.
Responda de forma direta, clara, técnica e personalizada em Português (Brasil) à pergunta do usuário usando o contexto real da telemetria, saúde mental e exames abaixo:

### DADOS DA ÚLTIMA NOITE & HOJE ({resumo_ctx['hoje_data']}):
- Sono Total: {resumo_ctx['hoje_sono_tot']}h | Profundo: {resumo_ctx['hoje_profundo']} min | REM: {resumo_ctx['hoje_rem']} min
- Readiness Score: {resumo_ctx['hoje_readiness']}/100 | Disposição: {resumo_ctx['hoje_disposicao']}/10
- Estado de Humor: {resumo_ctx['humor_hoje']} | Gatilhos: {resumo_ctx['gatilhos_hoje']} | Descompressão: {resumo_ctx['min_desc']} min

Pergunta do Usuário: "{pergunta_usuario}"
"""

        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt_chat,
                "stream": False,
                "keep_alive": "24h"
            }
            resp = requests.post(self.ollama_url, json=payload, timeout=300)
            if resp.status_code == 200:
                res_txt = resp.json().get("response", "").strip()
                if res_txt and len(res_txt) > 10:
                    return res_txt
            else:
                return f"⚠️ **Erro na API do Ollama (Status {resp.status_code}):** Verifique se o modelo '{self.model_name}' está baixado."
        except requests.exceptions.ConnectionError:
            return f"🔴 **Conexão Recusada:** O Ollama não está rodando em `{self.ollama_url}`."
        except requests.exceptions.Timeout:
            return "⏳ **Tempo de resposta esgotado:** O modelo local demorou mais de 5 minutos para processar."
        except Exception as err:
            return f"⚠️ **Erro inesperado:** `{err}`"

        return "⚠️ Não foi possível obter resposta do modelo Llama 3 local."
