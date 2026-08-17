import importlib
import os
import sys
import traceback
import streamlit as st
from core.base_plugin import BasePlugin


def load_plugins(modules_dir: str = "modules") -> dict[str, BasePlugin]:
    """Varre a pasta de módulos e carrega dinamicamente apenas as classes que herdam de BasePlugin."""
    plugins = {}

    if not os.path.exists(modules_dir):
        os.makedirs(modules_dir)
        return plugins

    # Garante que a pasta modules está no path do Python
    if modules_dir not in sys.path:
        sys.path.append(modules_dir)

    for file in os.listdir(modules_dir):
        if file.endswith(".py") and not file.startswith("__"):
            # Ignora arquivos de serviço ou monitoramento em segundo plano
            if file.startswith("monitor_") or file.startswith("service_"):
                continue

            module_name = file[:-3]
            try:
                # Importa o módulo dinamicamente
                imported_module = importlib.import_module(module_name)
                # Recarrega o módulo para refletir alterações em tempo de execução sem reiniciar o servidor
                importlib.reload(imported_module)

                # Procura por classes que herdam de BasePlugin
                for attr_name in dir(imported_module):
                    attr = getattr(imported_module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin
                    ):
                        instance = attr()
                        plugins[instance.title] = instance
            except Exception:
                # Ignora silenciosamente arquivos que não são plugins válidos de interface
                pass

    return plugins


def render_plugin_safely(plugin: BasePlugin) -> None:
    """Isola a execução do módulo em uma barreira de proteção contra crashes."""
    try:
        plugin.render()
    except Exception as e:
        st.error(
            f"⚠️ O módulo **{plugin.title}** encontrou um erro e foi interrompido.")
        st.info("O restante da Central de Comando continua operando normalmente.")
        with st.expander("Detalhes do erro técnico (StackTrace)"):
            st.code(traceback.format_exc(), language="python")
