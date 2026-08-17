from datetime import datetime
import streamlit as st
import pandas as pd
from core.base_plugin import BasePlugin

from services.db import DatabaseService
from reports.correlation_engine import CorrelationEngine
from reports.pdf_generator import PDFReportGenerator
from reports.ai_health_assistant import AIHealthAssistant

from views.tab_lancamentos import render_tab_lancamentos
from views.tab_saude_mental import render_tab_saude_mental
from views.tab_dashboard import render_tab_dashboard
from views.tab_exames import render_tab_exames
from views.tab_gerenciador import render_tab_gerenciador
from views.tab_biometria import render_tab_biometria
from views.tab_nutricao import render_tab_nutricao


class QualidadeVidaPlugin(BasePlugin):
    def __init__(self):
        self.db = DatabaseService()
        self.correlation_engine = CorrelationEngine()
        self.pdf_generator = PDFReportGenerator()
        self.ai_assistant = AIHealthAssistant()

    @property
    def title(self) -> str:
        return "Qualidade de Vida"

    @property
    def icon(self) -> str:
        return "🌱"

    def _injetar_css_customizado(self):
        st.markdown("""
        <style>
            .stApp, .main, div[data-testid="stAppViewContainer"], div[data-testid="stHeader"] {
                background-color: #0B0F19 !important;
                color: #F8FAFC !important;
            }

            section[data-testid="stSidebar"], [data-testid="stSidebar"] > div:first-child {
                background-color: #1E293B !important;
                border-right: 1px solid #334155 !important;
            }

            section[data-testid="stSidebar"] *, [data-testid="stSidebar"] * {
                color: #F8FAFC !important;
            }

            [data-testid="stIconMaterial"], 
            span:has(> [data-testid="stIconMaterial"]) {
                font-size: 0px !important;
            }

            h1, h2, h3, h4, h5, h6, label, p, span, div {
                color: #F8FAFC !important;
                font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
            }

            div[data-testid="stExpander"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
                margin-bottom: 12px !important;
            }
            div[data-testid="stExpander"] summary {
                color: #F8FAFC !important;
                background-color: #1E293B !important;
            }

            div[data-testid="stForm"] {
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
                padding: 20px !important;
                background-color: #1E293B !important;
            }

            .stTextInput > div > div > input, 
            .stNumberInput > div > div > input, 
            .stSelectbox > div > div, 
            .stTextArea textarea {
                background-color: #0F172A !important;
                color: #F8FAFC !important;
                border-radius: 8px !important;
                border: 1px solid #334155 !important;
                font-weight: 500 !important;
            }
            
            .stTextInput > div > div > input:focus, 
            .stNumberInput > div > div > input:focus,
            .stTextArea textarea:focus {
                border-color: #38BDF8 !important;
                box-shadow: 0 0 0 2px #38BDF840 !important;
            }

            .stButton > button, .stDownloadButton > button {
                background-color: #2563EB !important;
                color: #FFFFFF !important;
                font-weight: 700 !important;
                border-radius: 8px !important;
                border: 1px solid #334155 !important;
                padding: 10px 20px !important;
                font-size: 14px !important;
                box-shadow: 0 2px 6px rgba(0,0,0,0.25) !important;
                transition: all 0.2s ease-in-out !important;
            }
            .stButton > button:hover, .stDownloadButton > button:hover {
                background-color: #1D4ED8 !important;
                color: #FFFFFF !important;
                border-color: #38BDF8 !important;
                transform: translateY(-1px) !important;
            }

            .stButton > button[kind="primary"] {
                background-color: #38BDF8 !important;
                color: #0F172A !important;
                border: none !important;
            }

            div[data-testid="stMetric"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
                padding: 16px !important;
            }
            div[data-testid="stMetricLabel"] {
                color: #94A3B8 !important;
            }
            div[data-testid="stMetricValue"] {
                color: #38BDF8 !important;
                font-size: 26px !important;
                font-weight: 800 !important;
            }

            .stTabs [data-baseweb="tab-list"] {
                background-color: #1E293B !important;
                border: 1px solid #334155 !important;
                border-radius: 12px !important;
                padding: 6px !important;
                gap: 6px !important;
            }
            .stTabs [data-baseweb="tab"] {
                border-radius: 8px !important;
                padding: 8px 16px !important;
                font-weight: 600 !important;
                color: #94A3B8 !important;
                border: none !important;
            }
            .stTabs [aria-selected="true"] {
                background-color: #2563EB !important;
                color: #FFFFFF !important;
                font-weight: 700 !important;
            }

            div[data-testid="stTable"], .stDataFrame {
                background-color: #1E293B !important;
                border-radius: 10px !important;
                border: 1px solid #334155 !important;
            }
        </style>
        """, unsafe_allow_html=True)

    def render(self) -> None:
        self._injetar_css_customizado()
        self.db.inicializar_banco()
        metas_user = self.correlation_engine.carregar_metas_usuario()
        dispositivo_ativo = self.db.obter_dispositivo_ativo()

        st.title("🌱 Qualidade de Vida & Saúde")
        st.caption(
            f"Central de telemetria pessoal integrada com métricas do {dispositivo_ativo}.")

        e_visitante = st.query_params.get("view") == "read_only"

        if e_visitante:
            st.info(
                "👁️ **Modo Visualização Ativo:** Você está acessando em modo somente leitura.")
            aba_dashboard, aba_biometria, aba_nutricao, aba_exames, aba_mental, aba_ficha = st.tabs([
                "📊 Dashboard & Relatório",
                "⚖️ Composição Corporal",
                "🍎 Nutrição & TDEE",
                "🩺 Exames Laboratoriais",
                "🧠 Saúde Mental",
                "📑 Ficha Médica"
            ])
            aba_registro = None
            aba_gerenciador = None
        else:
            aba_registro, aba_gerenciador, aba_dashboard, aba_biometria, aba_nutricao, aba_exames, aba_mental, aba_ficha = st.tabs([
                "📝 Lançamentos por Seção",
                "⚙️ Atalhos & Configurações",
                "📊 Dashboard & Relatório",
                "⚖️ Composição Corporal",
                "🍎 Nutrição & TDEE",
                "🩺 Exames Laboratoriais",
                "🧠 Saúde Mental",
                "📑 Ficha Médica"
            ])

        if aba_registro is not None:
            with aba_registro:
                render_tab_lancamentos(self.db, self.ai_assistant, metas_user)

        if aba_gerenciador is not None:
            with aba_gerenciador:
                render_tab_gerenciador(self.db, metas_user)

        with aba_dashboard:
            render_tab_dashboard(
                self.db, self.ai_assistant, self.correlation_engine, self.pdf_generator, metas_user)

        with aba_biometria:
            render_tab_biometria(self.db)

        with aba_nutricao:
            render_tab_nutricao(self.db, self.ai_assistant)

        with aba_exames:
            render_tab_exames(self.db)

        with aba_mental:
            render_tab_saude_mental(self.db, self.ai_assistant)

        with aba_ficha:
            dados_ficha = self.db.carregar_ficha_medica()
            df_biometria = self.db.buscar_historico_telemetria()
            sups_ativos = self.db.buscar_suplementos_cadastrados()
            df_exames = self.db.buscar_historico_exames()

            f_head1, f_head2 = st.columns([3, 1])
            f_head1.subheader("📑 Ficha Médica & Dossiê Clínico")

            try:
                dossie_pdf_bytes = self.pdf_generator.gerar_dossie_clinico_pdf(
                    dados_ficha, df_biometria, sups_ativos, df_exames
                )
                if dossie_pdf_bytes:
                    nome_dossie = f"dossie_clinico_{datetime.now().strftime('%Y%m%d')}.pdf"
                    f_head2.download_button(
                        label="📥 Baixar Dossiê Médico (PDF)",
                        data=dossie_pdf_bytes,
                        file_name=nome_dossie,
                        mime="application/pdf",
                        width="stretch"
                    )
            except Exception as e_pdf:
                st.error(f"Erro ao gerar Dossiê em PDF: {e_pdf}")

            st.markdown("---")

            with st.form("form_ficha_medica_view"):
                f1, f2 = st.columns(2)
                tipo_sangue = f1.selectbox("Tipo Sanguíneo", [
                                           "O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-", "Não sei"], index=0)
                plano_saude = f2.text_input(
                    "Plano de Saúde", value=dados_ficha.get('plano_saude', ''))
                alergias = st.text_area(
                    "Alergias", value=dados_ficha.get('alergias', ''))
                condicoes = st.text_area(
                    "Condições Crônicas", value=dados_ficha.get('condicoes_cronicas', ''))
                historico_fam = st.text_area(
                    "Histórico Familiar", value=dados_ficha.get('historico_familiar', ''))
                vacinas = st.text_area(
                    "Vacinas", value=dados_ficha.get('vacinas', ''))
                emergencia = st.text_input(
                    "Contato Emergência", value=dados_ficha.get('contato_emergencia', ''))

                if st.form_submit_button("💾 Salvar Ficha Médica"):
                    self.db.salvar_ficha_medica_campo(
                        'tipo_sanguineo', tipo_sangue)
                    self.db.salvar_ficha_medica_campo(
                        'plano_saude', plano_saude)
                    self.db.salvar_ficha_medica_campo('alergias', alergias)
                    self.db.salvar_ficha_medica_campo(
                        'condicoes_cronicas', condicoes)
                    self.db.salvar_ficha_medica_campo(
                        'historico_familiar', historico_fam)
                    self.db.salvar_ficha_medica_campo('vacinas', vacinas)
                    self.db.salvar_ficha_medica_campo(
                        'contato_emergencia', emergencia)
                    st.success("Ficha médica atualizada!")
                    st.rerun()
