import sys
import asyncio
import sqlite3
import streamlit as st

# Fix para silenciar exceções de desconexão de sockets no Windows (WinError 10054)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from core.loader import load_plugins, render_plugin_safely

ARQUIVO_DB = "telemetria.db"

# Configuração da página e janela do navegador
st.set_page_config(
    page_title="Central Saúde",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)


def render_sidebar_settings():
    st.sidebar.markdown("---")

    # Expander de Configurações na Sidebar
    with st.sidebar.expander("⚙️ Settings & Manutenção", expanded=False):
        st.caption("Ferramentas de depuração para zerar registros de testes.")

        # 1. Seleção da Tabela do Banco de Dados
        tabelas_disponiveis = [
            "QualidadeVida",
            "SessoesTreino",
            "ExamesLaboratoriais",
            "SaudeMentalLogs",
            "SessaoTerapeuticaChat",
            "SuplementosLogs",
            "suplementos_custom",
            "recipientes_custom",
            "modalidades_custom",
            "fichas_treino_custom",
            "ficha_medica",
            "metas_config"
        ]
        tabela_sel = st.selectbox("Selecione a Tabela", tabelas_disponiveis)

        # 2. Modo de Limpeza
        modo_limpeza = st.radio(
            "Escopo da Limpeza",
            ["Apenas um dia específico", "Zerar TODA a tabela"],
            index=0
        )

        data_limpeza = None
        if modo_limpeza == "Apenas um dia específico":
            data_limpeza = st.date_input(
                "Data para Limpar", value=st.session_state.get("data_ref", None) or "today")

        st.markdown("---")

        # 3. Ação de Exclusão com Confirmação
        if st.button("🗑️ Executar Limpeza", type="primary", width="stretch"):
            try:
                conn = sqlite3.connect(ARQUIVO_DB)
                cursor = conn.cursor()

                if modo_limpeza == "Apenas um dia específico" and data_limpeza:
                    data_str = data_limpeza.strftime('%Y-%m-%d')

                    if tabela_sel == "QualidadeVida":
                        cursor.execute(
                            "DELETE FROM QualidadeVida WHERE DataRegistro = ?", (data_str,))
                    elif tabela_sel == "SessoesTreino":
                        cursor.execute(
                            "DELETE FROM SessoesTreino WHERE data_registro = ?", (data_str,))
                    elif tabela_sel == "SaudeMentalLogs":
                        cursor.execute(
                            "DELETE FROM SaudeMentalLogs WHERE data_registro = ?", (data_str,))
                    elif tabela_sel == "SessaoTerapeuticaChat":
                        cursor.execute(
                            "DELETE FROM SessaoTerapeuticaChat WHERE data_registro = ?", (data_str,))
                    elif tabela_sel == "SuplementosLogs":
                        cursor.execute(
                            "DELETE FROM SuplementosLogs WHERE data_registro = ?", (data_str,))
                    elif tabela_sel == "ExamesLaboratoriais":
                        cursor.execute(
                            "DELETE FROM ExamesLaboratoriais WHERE data_exame = ?", (data_str,))
                    else:
                        st.warning(
                            f"A tabela '{tabela_sel}' não possui campo de data diária para filtro.")
                        conn.close()
                        return

                    conn.commit()
                    st.success(
                        f"Registros de {data_str} removidos da tabela '{tabela_sel}'!")

                else:  # Zerar toda a tabela
                    cursor.execute(f"DELETE FROM {tabela_sel}")
                    cursor.execute(
                        "DELETE FROM sqlite_sequence WHERE name = ?", (tabela_sel,))
                    conn.commit()
                    st.success(
                        f"Tabela '{tabela_sel}' foi completamente zerada!")

                conn.close()
                st.rerun()

            except Exception as e:
                st.error(f"Erro ao executar limpeza no banco: {e}")


# Inicialização da Barra Lateral
st.sidebar.title("🌱 Central Saúde")
st.sidebar.caption("v1.0.0-RELEASE")
st.sidebar.markdown("---")

# Carregamento seguro e resiliente dos módulos
try:
    available_plugins = load_plugins()
except Exception:
    available_plugins = {}

if not available_plugins:
    st.warning("Nenhum módulo ativo encontrado na pasta `modules/`.")
else:
    # Monta a seleção na Sidebar dinamicamente baseado nos plugins válidos carregados
    options = list(available_plugins.keys())
    selected_option = st.sidebar.radio(
        "Navegação",
        options,
        format_func=lambda x: f"{available_plugins[x].icon} {x}"
    )

    # Renderiza o submenu de Settings na Sidebar
    render_sidebar_settings()

    # Renderiza o módulo selecionado dentro da barreira de proteção
    selected_plugin = available_plugins[selected_option]
    try:
        render_plugin_safely(selected_plugin)
    except Exception as e:
        st.error(
            f"Ocorreu um erro ao renderizar o módulo '{selected_option}': {e}")
