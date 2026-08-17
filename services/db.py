import sqlite3
import re
import pandas as pd
import streamlit as st

try:
    import pdfplumber
    PDFPLUMBER_DISPONIVEL = True
except ImportError:
    PDFPLUMBER_DISPONIVEL = False

ARQUIVO_DB = "telemetria.db"


class DatabaseService:
    def __init__(self, db_path=ARQUIVO_DB):
        self.db_path = db_path

    def _get_connection(self):
        """Retorna uma conexão configurada com suporte a acesso por nome de coluna."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- 1. AJUSTE DE ESQUEMA E MIGRATION DO BANCO ---
    def inicializar_banco(self):
        """Garante a criação de todas as tabelas e colunas necessárias no SQLite."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Tabela Principal de Telemetria
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS QualidadeVida (
                        Id INTEGER PRIMARY KEY AUTOINCREMENT,
                        DataRegistro DATE UNIQUE DEFAULT (DATE('now', 'localtime'))
                    )
                ''')

                # Recipientes
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS recipientes_custom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tipo TEXT NOT NULL,
                        nome TEXT NOT NULL,
                        volume_ml INTEGER NOT NULL,
                        fator_cafeina REAL DEFAULT 0.6
                    )
                ''')

                # Sessões de Treino
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS SessoesTreino (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_registro DATE NOT NULL,
                        modalidade TEXT NOT NULL,
                        duracao_minutos INTEGER DEFAULT 0,
                        calorias_queimadas INTEGER DEFAULT 0,
                        distancia_km REAL DEFAULT 0.0,
                        pace_medio TEXT,
                        bpm_medio INTEGER DEFAULT 0,
                        bpm_maximo INTEGER DEFAULT 0,
                        sensacao_pos_treino INTEGER DEFAULT 5,
                        sintomas_pos_treino TEXT,
                        notas_treino TEXT
                    )
                ''')

                # Modalidades Customizadas
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS modalidades_custom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL UNIQUE,
                        icone TEXT NOT NULL DEFAULT '🏋️',
                        pede_distancia BOOLEAN DEFAULT 0,
                        pede_pace BOOLEAN DEFAULT 0,
                        pede_bpm BOOLEAN DEFAULT 1
                    )
                ''')

                # Exames Laboratoriais
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ExamesLaboratoriais (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_exame DATE NOT NULL,
                        laboratorio TEXT,
                        marcador TEXT NOT NULL,
                        resultado REAL NOT NULL,
                        unidade TEXT,
                        referencia_min REAL,
                        referencia_max REAL,
                        categoria TEXT,
                        observacoes TEXT
                    )
                ''')

                # Suplementos / Fármacos
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS suplementos_custom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome TEXT NOT NULL UNIQUE,
                        dose TEXT NOT NULL,
                        horario TEXT NOT NULL DEFAULT 'Manhã',
                        categoria_acao TEXT DEFAULT 'Geral',
                        mecanismo TEXT DEFAULT '',
                        ativo BOOLEAN DEFAULT 1
                    )
                ''')

                # Logs de Suplementos
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS SuplementosLogs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_registro DATE NOT NULL,
                        suplemento_id INTEGER NOT NULL,
                        tomado BOOLEAN DEFAULT 0,
                        UNIQUE(data_registro, suplemento_id)
                    )
                ''')

                # Configurações de Metas & Preferências do Usuário
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS metas_config (
                        chave TEXT PRIMARY KEY,
                        valor TEXT NOT NULL
                    )
                ''')

                # Ficha Médica
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS ficha_medica (
                        chave TEXT PRIMARY KEY,
                        valor TEXT NOT NULL
                    )
                ''')

                # Templates de Treino
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS fichas_treino_custom (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nome_ficha TEXT NOT NULL UNIQUE,
                        modalidade TEXT NOT NULL,
                        duracao_est_min INTEGER DEFAULT 45,
                        calorias_est_kcal INTEGER DEFAULT 300,
                        bpm_medio_est INTEGER DEFAULT 125,
                        pse_est INTEGER DEFAULT 6,
                        exercicios_detalhe TEXT,
                        ativo BOOLEAN DEFAULT 1
                    )
                ''')

                # Saúde Mental Logs
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS SaudeMentalLogs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_registro DATE NOT NULL UNIQUE,
                        humor_score INTEGER DEFAULT 5,
                        estado_emocional TEXT DEFAULT 'Neutro',
                        gatilhos TEXT,
                        minutos_descompressao INTEGER DEFAULT 0,
                        atividade_descompressao TEXT,
                        diario_tcc_pensamento TEXT,
                        diario_tcc_reenquadramento TEXT
                    )
                ''')

                # Chat Terapêutico Contínuo
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS SessaoTerapeuticaChat (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        data_registro DATE NOT NULL,
                        origem TEXT NOT NULL,
                        mensagem TEXT NOT NULL,
                        timestamp DATETIME DEFAULT (DATETIME('now', 'localtime'))
                    )
                ''')

                # Carga Inicial de Dados Estáticos (se vazios)
                cursor.execute("SELECT COUNT(*) FROM metas_config")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany('''
                        INSERT INTO metas_config (chave, valor) VALUES (?, ?)
                    ''', [
                        ('meta_passos', '8000'),
                        ('meta_sono_horas', '7.0'),
                        ('meta_score_sono', '75'),
                        ('limite_cafe_ml', '300'),
                        ('meta_agua_auto', '1'),
                        ('meta_agua_fixa_ml', '2500'),
                        ('dispositivo_wearable', 'Smartwatch / Wearable')
                    ])

                cursor.execute("SELECT COUNT(*) FROM recipientes_custom")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany('''
                        INSERT INTO recipientes_custom (tipo, nome, volume_ml, fator_cafeina) VALUES (?, ?, ?, ?)
                    ''', [
                        ('agua', 'Copo Padrão', 250, 0.0),
                        ('agua', 'Garrafa Média', 500, 0.0),
                        ('agua', 'Squeeze', 750, 0.0),
                        ('cafeina', 'Espresso Simples (80ml)', 80, 0.6),
                        ('cafeina', 'Café Coado (100ml)', 100, 0.6),
                        ('cafeina', 'Lata de Energético (473ml)', 473, 0.32),
                        ('cafeina', 'Lata de Refrigerante (350ml)', 350, 0.10)
                    ])

                cursor.execute("SELECT COUNT(*) FROM modalidades_custom")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany('''
                        INSERT OR IGNORE INTO modalidades_custom (nome, icone, pede_distancia, pede_pace, pede_bpm) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', [
                        ('Musculação', '🏋️', 0, 0, 1),
                        ('Corrida', '🏃', 1, 1, 1),
                        ('Caminhada', '🚶', 1, 1, 1),
                        ('Ciclismo', '🚴', 1, 1, 1),
                        ('Natação', '🏊', 1, 0, 1)
                    ])

                cursor.execute("SELECT COUNT(*) FROM suplementos_custom")
                if cursor.fetchone()[0] == 0:
                    cursor.executemany('''
                        INSERT OR IGNORE INTO suplementos_custom (nome, dose, horario, categoria_acao, mecanismo) 
                        VALUES (?, ?, ?, ?, ?)
                    ''', [
                        ('Creatina Monohidratada', '5g', 'Pós-Treino / Manhã',
                         'Recuperação Muscular / Força', 'Ressíntese de ATP e hidratação celular'),
                        ('Vitamina D3', '2.000 UI', 'Manhã',
                         'Saúde Cardiovascular / Antioxidante', 'Modulação imune e hormonal'),
                        ('Ômega 3', '1000mg', 'Almoço', 'Saúde Cardiovascular / Antioxidante',
                         'Redução do perfil inflamatório'),
                        ('Magnésio Inositol', '300mg', 'Noite', 'Indutor de Sono / Relaxante',
                         'Ativação do sistema GABA e relaxamento muscular')
                    ])

                # Verificação de colunas em QualidadeVida
                colunas_desejadas = {
                    "Passos": "INTEGER DEFAULT 0",
                    "CaloriasQueimadas": "INTEGER DEFAULT 0",
                    "MinutosAtivos": "INTEGER DEFAULT 0",
                    "ExercicioRealizado": "BOOLEAN DEFAULT 0",
                    "TipoExercicio": "TEXT",
                    "HorasSono": "REAL DEFAULT 0.0",
                    "QualidadeSonoScore": "INTEGER DEFAULT 0",
                    "FrequenciaCardiacaRepouso": "INTEGER DEFAULT 0",
                    "NivelEstresseScore": "INTEGER DEFAULT 0",
                    "NivelEnergiaScore": "INTEGER DEFAULT 0",
                    "ConsumoAguaML": "INTEGER DEFAULT 0",
                    "ConsumoCafeinaMG": "INTEGER DEFAULT 0",
                    "ConsumoCafeML": "INTEGER DEFAULT 0",
                    "PesoKG": "REAL",
                    "PercentualGordura": "REAL",
                    "MusculoEsqueleticoKG": "REAL",
                    "MassaGordaKG": "REAL",
                    "AguaCorporalKG": "REAL",
                    "TMBKcal": "INTEGER",
                    "Observacoes": "TEXT",
                    "DisposicaoAcordarScore": "INTEGER DEFAULT 5",
                    "FocoClarezaScore": "INTEGER DEFAULT 5",
                    "DorMuscularScore": "INTEGER DEFAULT 0",
                    "ConfortoDigestivoScore": "INTEGER DEFAULT 8",
                    "SonoProfundoMinutos": "INTEGER DEFAULT 0",
                    "SonoREMMinutos": "INTEGER DEFAULT 0",
                    "TempoAcordadoMinutos": "INTEGER DEFAULT 0",
                    "LatenciaSonoMinutos": "INTEGER DEFAULT 0",
                    "SpO2MedioPct": "REAL DEFAULT 96.5",
                    "FreqRespiratoriaMedio": "REAL DEFAULT 14.5",
                    "ScoreProntitudade": "INTEGER DEFAULT 75"
                }

                cursor.execute("PRAGMA table_info(QualidadeVida)")
                colunas_existentes = [linha[1] for linha in cursor.fetchall()]
                for coluna, tipo in colunas_desejadas.items():
                    if coluna not in colunas_existentes:
                        cursor.execute(
                            f"ALTER TABLE QualidadeVida ADD COLUMN {coluna} {tipo}")

                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao inicializar schema do banco: {e}")
            return False

    # --- 2. GESTÃO DE PERFIL E PREFERÊNCIAS DO USUÁRIO ---
    def obter_dispositivo_ativo(self) -> str:
        """Retorna o perfil de smartwatch/smartband cadastrado no banco com fallback genérico."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT valor FROM metas_config WHERE chave = 'dispositivo_wearable'")
                row = cursor.fetchone()
                return row[0] if row and row[0] else "Smartwatch / Wearable"
        except Exception:
            return "Smartwatch / Wearable"

    # --- 3. CÁLCULO DE MILESTONES E STREAKS ---
    def calcular_milestones_e_streaks(self) -> dict:
        """Calcula totais acumulados, sequências ininterruptas (streaks) e marcos atingidos."""
        res = {
            "total_passos_acumulados": 0,
            "total_dias_registrados": 0,
            "streak_agua_dias": 0,
            "streak_sono_dias": 0,
            "streak_treino_dias": 0,
            "badges": []
        }
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT SUM(Passos), COUNT(*) FROM QualidadeVida WHERE Passos > 0")
                row_tot = cursor.fetchone()
                res["total_passos_acumulados"] = int(row_tot[0] or 0)
                res["total_dias_registrados"] = int(row_tot[1] or 0)

                cursor.execute(
                    "SELECT DataRegistro, ConsumoAguaML, HorasSono, Passos FROM QualidadeVida ORDER BY DataRegistro DESC")
                rows = cursor.fetchall()

            meta_agua = 2500
            meta_sono = 7.0

            s_agua, s_sono, s_treino = 0, 0, 0
            for i, r in enumerate(rows):
                agua = int(r[1] or 0)
                sono = float(r[2] or 0.0)
                passos = int(r[3] or 0)

                if agua >= meta_agua:
                    s_agua += 1
                elif i == 0:
                    s_agua = 0

                if sono >= meta_sono:
                    s_sono += 1
                elif i == 0:
                    s_sono = 0

                if passos >= 5000:
                    s_treino += 1
                elif i == 0:
                    s_treino = 0

            res["streak_agua_dias"] = s_agua
            res["streak_sono_dias"] = s_sono
            res["streak_treino_dias"] = s_treino

            if res["total_passos_acumulados"] >= 500000:
                res["badges"].append(
                    {"titulo": "🏃‍♂️ Meio Milhão de Passos", "desc": "Mais de 500k passos gravados no banco!"})
            elif res["total_passos_acumulados"] >= 100000:
                res["badges"].append(
                    {"titulo": "🚶‍♂️ Centenário de Passos", "desc": "100k passos acumulados na jornada!"})

            if s_agua >= 7:
                res["badges"].append(
                    {"titulo": "💧 Mestre da Hidratação", "desc": "7+ dias seguidos cumprindo a meta de água!"})

            if s_sono >= 5:
                res["badges"].append(
                    {"titulo": "😴 Sono Reparador", "desc": "5+ dias seguidos com 7h+ de sono!"})

            return res
        except Exception:
            return res

    # --- 4. PARSER & ALERTAS DE EXAMES LABORATORIAIS ---
    def buscar_alertas_exames_recentes(self) -> list[dict]:
        """Verifica a coleta de exames mais recente e retorna os marcadores fora de referência."""
        alertas = []
        try:
            with self._get_connection() as conn:
                df_exames = pd.read_sql_query(
                    "SELECT * FROM ExamesLaboratoriais ORDER BY data_exame DESC", conn)

            if df_exames.empty:
                return alertas

            data_recente = df_exames['data_exame'].max()
            df_rec = df_exames[df_exames['data_exame'] == data_recente]

            for _, row in df_rec.iterrows():
                res = float(row['resultado'])
                rmin = float(row['referencia_min']) if pd.notnull(
                    row['referencia_min']) else None
                rmax = float(row['referencia_max']) if pd.notnull(
                    row['referencia_max']) else None

                if rmin is not None and res < rmin:
                    alertas.append({
                        "marcador": row['marcador'],
                        "valor": res,
                        "unidade": row['unidade'] or "",
                        "status": f"Abaixo do mínimo ({rmin})",
                        "nivel": "warning"
                    })
                elif rmax is not None and res > rmax:
                    alertas.append({
                        "marcador": row['marcador'],
                        "valor": res,
                        "unidade": row['unidade'] or "",
                        "status": f"Acima do máximo ({rmax})",
                        "nivel": "danger"
                    })
            return alertas
        except Exception:
            return alertas

    def _extrair_texto_pdf_exame(self, arquivo_pdf) -> tuple[str, str]:
        if not PDFPLUMBER_DISPONIVEL:
            return "", ""
        try:
            texto_completo = ""
            data_coleta = ""

            with pdfplumber.open(arquivo_pdf) as pdf:
                for pagina in pdf.pages:
                    t = pagina.extract_text()
                    if t:
                        texto_completo += t + "\n"
                        match_data = re.search(
                            r"Coleta:\s*(\d{2}/\d{2}/\d{4})", t, re.IGNORECASE)
                        if match_data and not data_coleta:
                            data_coleta = match_data.group(1)

            return texto_completo, data_coleta
        except Exception as e:
            st.error(f"Erro ao ler arquivo PDF com pdfplumber: {e}")
            return "", ""

    def _parse_exames_sabin_especifico(self, texto: str) -> list[dict]:
        resultados = []
        linhas = [l.strip() for l in texto.split('\n') if l.strip()]

        categorias_map = {
            "HEMÁCIAS": ("Eritrograma", "milhoes/mm3", 4.5, 6.1),
            "HEMOGLOBINA": ("Eritrograma", "g/dL", 13.0, 16.5),
            "HEMATÓCRITO": ("Eritrograma", "%", 36.0, 54.0),
            "VCM": ("Eritrograma", "fL", 80.0, 98.0),
            "HCM": ("Eritrograma", "pg", 26.8, 32.9),
            "CHCM": ("Eritrograma", "g/dL", 30.0, 36.5),
            "RDW": ("Eritrograma", "%", 11.0, 16.0),
            "LEUCÓCITOS": ("Leucograma", "/mm3", 3600.0, 11000.0),
            "BASTONETES": ("Leucograma", "/mm3", 0.0, 550.0),
            "SEGMENTADOS": ("Leucograma", "/mm3", 1480.0, 7700.0),
            "EOSINÓFILOS": ("Leucograma", "/mm3", 0.0, 550.0),
            "BASÓFILOS": ("Leucograma", "/mm3", 0.0, 220.0),
            "LINFÓCITOS": ("Leucograma", "/mm3", 740.0, 5500.0),
            "MONÓCITOS": ("Leucograma", "/mm3", 37.0, 1500.0),
            "PLAQUETAS": ("Plaquetas", "x 10³/mm3", 130.0, 450.0),
            "VMP": ("Plaquetas", "fL", 6.8, 12.6),
            "GLICOSE": ("Glicemia", "mg/dL", 70.0, 99.0),
            "COLESTEROL TOTAL": ("Perfil Lipídico", "mg/dL", 0.0, 190.0),
            "COLESTEROL HDL": ("Perfil Lipídico", "mg/dL", 40.0, 100.0),
            "COLESTEROL LDL": ("Perfil Lipídico", "mg/dL", 0.0, 130.0),
            "COLESTEROL NAO HDL": ("Perfil Lipídico", "mg/dL", 0.0, 130.0),
            "TRIGLICERÍDEOS": ("Perfil Lipídico", "mg/dL", 0.0, 150.0),
            "TRIGLICERIDES": ("Perfil Lipídico", "mg/dL", 0.0, 150.0),
            "CREATININA": ("Renal", "mg/dL", 0.7, 1.3),
            "UREIA": ("Renal", "mg/dL", 15.0, 45.0),
            "TSH": ("Hormonal", "mUI/L", 0.4, 4.5),
            "TESTOSTERONA TOTAL": ("Hormonal", "ng/dL", 240.0, 870.0)
        }

        lixo_palavras = ['valores de referência', 'método:', 'material:',
                         'liberação:', 'revisado e liberado', 'acima de', 'menor que', 'pesquisa']

        for linha in linhas:
            if any(lixo in linha.lower() for lixo in lixo_palavras):
                continue

            for marcador_chave, (cat, und_padrao, r_min, r_max) in categorias_map.items():
                if linha.upper().startswith(marcador_chave):
                    numeros = re.findall(r"\d+[\.,]?\d*", linha)
                    if numeros:
                        try:
                            if cat == "Leucograma" and len(numeros) >= 2:
                                val_raw = numeros[1]
                            else:
                                val_raw = numeros[0]

                            val_str = val_raw.replace('.', '').replace(
                                ',', '.') if '.' in val_raw and ',' in val_raw else val_raw.replace(',', '.')
                            val_num = float(val_str)

                            resultados.append({
                                "marcador": marcador_chave,
                                "resultado": val_num,
                                "unidade": und_padrao,
                                "referencia_min": r_min,
                                "referencia_max": r_max,
                                "categoria": cat
                            })
                            break
                        except ValueError:
                            continue

        return resultados

    # --- 5. LEITURA DE DADOS ---
    def buscar_registro_por_data(self, data_str: str) -> dict:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM QualidadeVida WHERE DataRegistro = ?", (data_str,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def buscar_historico_telemetria(self, limite=30) -> pd.DataFrame:
        try:
            with self._get_connection() as conn:
                query = f"SELECT * FROM QualidadeVida ORDER BY DataRegistro DESC LIMIT {limite}"
                return pd.read_sql_query(query, conn)
        except Exception:
            return pd.DataFrame()

    def buscar_sessoes_treino(self, data_str: str) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM SessoesTreino WHERE data_registro = ? ORDER BY id DESC", (data_str,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def buscar_modalidades(self) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM modalidades_custom ORDER BY nome ASC")
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def buscar_recipientes(self, tipo: str) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM recipientes_custom WHERE tipo = ? ORDER BY volume_ml ASC", (tipo,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def buscar_suplementos_cadastrados(self) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM suplementos_custom WHERE ativo = 1 ORDER BY horario ASC, nome ASC")
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def buscar_logs_suplementos_data(self, data_str: str) -> dict:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT suplemento_id, tomado FROM SuplementosLogs WHERE data_registro = ?", (data_str,))
                return {r[0]: bool(r[1]) for r in cursor.fetchall()}
        except Exception:
            return {}

    def buscar_fichas_treino(self) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM fichas_treino_custom WHERE ativo = 1 ORDER BY nome_ficha ASC")
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    def buscar_historico_exames(self) -> pd.DataFrame:
        try:
            with self._get_connection() as conn:
                return pd.read_sql_query("SELECT * FROM ExamesLaboratoriais ORDER BY data_exame DESC, marcador ASC", conn)
        except Exception:
            return pd.DataFrame()

    def carregar_ficha_medica(self) -> dict:
        dados = {
            "tipo_sanguineo": "Não informado", "alergias": "Nenhuma informada",
            "condicoes_cronicas": "Nenhuma", "historico_familiar": "Sem histórico relevante",
            "vacinas": "Em dia", "plano_saude": "Não informado", "contato_emergencia": "Não informado"
        }
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT chave, valor FROM ficha_medica")
                for k, v in cursor.fetchall():
                    if k in dados:
                        dados[k] = v
                return dados
        except Exception:
            return dados

    def buscar_registro_mental_data(self, data_str: str) -> dict:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM SaudeMentalLogs WHERE data_registro = ?", (data_str,))
                row = cursor.fetchone()
                return dict(row) if row else {}
        except Exception:
            return {}

    def buscar_historico_chat_terapeutico(self, data_str: str) -> list[dict]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT origem, mensagem FROM SessaoTerapeuticaChat WHERE data_registro = ? ORDER BY id ASC", (data_str,))
                return [dict(r) for r in cursor.fetchall()]
        except Exception:
            return []

    # --- 6. ESCRITA E ATUALIZAÇÃO DE DADOS ---
    def atualizar_secao_parcial(self, data_str: str, dados_secao: dict) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO QualidadeVida (DataRegistro) VALUES (?) ON CONFLICT(DataRegistro) DO NOTHING", (data_str,))
                set_clause = ", ".join(
                    [f"{col} = ?" for col in dados_secao.keys()])
                valores = list(dados_secao.values())
                valores.append(data_str)
                cursor.execute(
                    f"UPDATE QualidadeVida SET {set_clause} WHERE DataRegistro = ?", valores)
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao atualizar telemetria: {e}")
            return False

    def salvar_sessao_treino(self, dados: dict) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO SessoesTreino 
                    (data_registro, modalidade, duracao_minutos, calorias_queimadas, distancia_km, pace_medio, bpm_medio, bpm_maximo, sensacao_pos_treino, sintomas_pos_treino, notas_treino)
                    VALUES (:data_registro, :modalidade, :duracao_minutos, :calorias_queimadas, :distancia_km, :pace_medio, :bpm_medio, :bpm_maximo, :sensacao_pos_treino, :sintomas_pos_treino, :notas_treino)
                ''', dados)
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar sessão de treino: {e}")
            return False

    def deletar_sessao_treino(self, id_treino: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM SessoesTreino WHERE id = ?", (id_treino,))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_recipiente(self, tipo: str, nome: str, volume: int, fator_cafeina: float = 0.6) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO recipientes_custom (tipo, nome, volume_ml, fator_cafeina) VALUES (?, ?, ?, ?)",
                               (tipo, nome, volume, fator_cafeina))
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar recipiente: {e}")
            return False

    def deletar_recipiente(self, id_recipiente: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM recipientes_custom WHERE id = ?", (id_recipiente,))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_modalidade(self, nome: str, icone: str, pede_dist: bool, pede_pace: bool, pede_bpm: bool) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO modalidades_custom (nome, icone, pede_distancia, pede_pace, pede_bpm) 
                    VALUES (?, ?, ?, ?, ?)
                ''', (nome, icone, pede_dist, pede_pace, pede_bpm))
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar modalidade: {e}")
            return False

    def deletar_modalidade(self, id_mod: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM modalidades_custom WHERE id = ?", (id_mod,))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_suplemento_custom(self, nome: str, dose: str, horario: str, categoria: str = "Geral", mecanismo: str = "") -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO suplementos_custom (nome, dose, horario, categoria_acao, mecanismo, ativo) 
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (nome, dose, horario, categoria, mecanismo))
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar suplemento: {e}")
            return False

    def deletar_suplemento_custom(self, id_sup: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM suplementos_custom WHERE id = ?", (id_sup,))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_log_suplemento(self, data_str: str, suplemento_id: int, tomado: bool) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO SuplementosLogs (data_registro, suplemento_id, tomado)
                    VALUES (?, ?, ?)
                    ON CONFLICT(data_registro, suplemento_id) DO UPDATE SET tomado = excluded.tomado
                ''', (data_str, suplemento_id, 1 if tomado else 0))
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao registrar suplemento: {e}")
            return False

    def salvar_ficha_treino(self, nome_ficha: str, modalidade: str, duracao: int, calorias: int, bpm: int, pse: int, detalhe: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO fichas_treino_custom 
                    (nome_ficha, modalidade, duracao_est_min, calorias_est_kcal, bpm_medio_est, pse_est, exercicios_detalhe, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                ''', (nome_ficha, modalidade, duracao, calorias, bpm, pse, detalhe))
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar ficha de treino: {e}")
            return False

    def deletar_ficha_treino(self, id_ficha: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM fichas_treino_custom WHERE id = ?", (id_ficha,))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_meta_config(self, chave: str, valor: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO metas_config (chave, valor) VALUES (?, ?)", (chave, str(valor)))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_ficha_medica_campo(self, chave: str, valor: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO ficha_medica (chave, valor) VALUES (?, ?)", (chave, str(valor)))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_exames_lote(self, data_exame_str: str, laboratorio: str, df_exames: pd.DataFrame) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for _, row in df_exames.iterrows():
                    cursor.execute('''
                        INSERT INTO ExamesLaboratoriais 
                        (data_exame, laboratorio, marcador, resultado, unidade, referencia_min, referencia_max, categoria)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        data_exame_str,
                        laboratorio,
                        row['marcador'],
                        float(row['resultado']),
                        row['unidade'],
                        float(row['referencia_min']) if pd.notnull(
                            row['referencia_min']) else None,
                        float(row['referencia_max']) if pd.notnull(
                            row['referencia_max']) else None,
                        row['categoria']
                    ))
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar exames no banco: {e}")
            return False

    def limpar_exames_duplicados_banco(self) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM ExamesLaboratoriais 
                    WHERE id NOT IN (
                        SELECT MIN(id) 
                        FROM ExamesLaboratoriais 
                        GROUP BY data_exame, marcador
                    )
                ''')
                conn.commit()
                return True
        except Exception:
            return False

    def deletar_exame(self, id_exame: int) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM ExamesLaboratoriais WHERE id = ?", (id_exame,))
                conn.commit()
                return True
        except Exception:
            return False

    def salvar_registro_mental(self, dados: dict) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO SaudeMentalLogs 
                    (data_registro, humor_score, estado_emocional, gatilhos, minutos_descompressao, atividade_descompressao, diario_tcc_pensamento, diario_tcc_reenquadramento)
                    VALUES (:data_registro, :humor_score, :estado_emocional, :gatilhos, :minutos_descompressao, :atividade_descompressao, :diario_tcc_pensamento, :diario_tcc_reenquadramento)
                    ON CONFLICT(data_registro) DO UPDATE SET
                        humor_score = excluded.humor_score,
                        estado_emocional = excluded.estado_emocional,
                        gatilhos = excluded.gatilhos,
                        minutos_descompressao = excluded.minutos_descompressao,
                        atividade_descompressao = excluded.atividade_descompressao,
                        diario_tcc_pensamento = excluded.diario_tcc_pensamento,
                        diario_tcc_reenquadramento = excluded.diario_tcc_reenquadramento
                ''', dados)
                conn.commit()
                return True
        except Exception as e:
            st.error(f"Erro ao salvar diário de saúde mental: {e}")
            return False

    def salvar_mensagem_chat_terapeutico(self, data_str: str, origem: str, mensagem: str) -> bool:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO SessaoTerapeuticaChat (data_registro, origem, mensagem)
                    VALUES (?, ?, ?)
                ''', (data_str, origem, mensagem))
                conn.commit()
                return True
        except Exception:
            return False
