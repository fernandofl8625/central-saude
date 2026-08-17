from abc import ABC, abstractmethod

class BasePlugin(ABC):
    @property
    @abstractmethod
    def title(self) -> str:
        """Nome do módulo que aparecerá no menu."""
        pass

    @property
    @abstractmethod
    def icon(self) -> str:
        """Ícone (Emoji ou Material Icon) para a sidebar."""
        pass

    @abstractmethod
    def render(self) -> None:
        """Todo o código visual e de lógica do Streamlit entra aqui."""
        pass