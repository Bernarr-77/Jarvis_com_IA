"""
Módulo de memória persistente do JARVIS (SQLite).

Armazena o histórico de conversas entre o usuário e o JARVIS
para que ele mantenha contexto entre sessões. Quando o JARVIS
é iniciado, as últimas interações são carregadas e injetadas
na instrução de sistema para dar continuidade natural.
"""
import sqlite3
import logging
from datetime import datetime
from typing import List, Tuple

logger = logging.getLogger(__name__)

DB_PATH = "jarvis_memoria.db"


class MemoriaJarvis:
    """Gerenciador de memória persistente do JARVIS via SQLite.
    
    Responsabilidades:
        - Criar e manter a tabela de conversas
        - Salvar cada interação (usuário → JARVIS)
        - Recuperar as últimas N interações para contexto
        - Gerar um resumo formatado para injetar no prompt
    """

    def __init__(self, db_path: str = DB_PATH):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._criar_tabela()
        logger.info(f"Memoria JARVIS inicializada ({db_path})")

    def _criar_tabela(self) -> None:
        """Cria a tabela de conversas se não existir."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS conversas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                papel TEXT NOT NULL,
                mensagem TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def salvar(self, papel: str, mensagem: str) -> None:
        """Salva uma mensagem no histórico.
        
        Args:
            papel: 'usuario' ou 'jarvis'
            mensagem: Texto da mensagem
        """
        agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._conn.execute(
            "INSERT INTO conversas (timestamp, papel, mensagem) VALUES (?, ?, ?)",
            (agora, papel, mensagem)
        )
        self._conn.commit()

    def ultimas_interacoes(self, limite: int = 20) -> List[Tuple[str, str, str]]:
        """Retorna as últimas N interações (timestamp, papel, mensagem)."""
        cursor = self._conn.execute(
            "SELECT timestamp, papel, mensagem FROM conversas ORDER BY id DESC LIMIT ?",
            (limite,)
        )
        resultados = cursor.fetchall()
        resultados.reverse()  # Ordem cronológica
        return resultados

    def gerar_contexto(self, limite: int = 20) -> str:
        """Gera um bloco de texto com o histórico recente para injetar no prompt.
        
        Returns:
            String formatada com as últimas interações, pronta para
            ser incluída na instrução de sistema do Gemini.
        """
        interacoes = self.ultimas_interacoes(limite)
        if not interacoes:
            return ""

        linhas = ["[HISTORICO DE CONVERSAS ANTERIORES]"]
        for timestamp, papel, mensagem in interacoes:
            nome = "Senhor" if papel == "usuario" else "JARVIS"
            linhas.append(f"[{timestamp}] {nome}: {mensagem}")
        linhas.append("[FIM DO HISTORICO]")

        return "\n".join(linhas)

    def fechar(self) -> None:
        """Fecha a conexão com o banco."""
        self._conn.close()
