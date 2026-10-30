"""Configuração: fontes RSS por categoria e parâmetros do pipeline."""
import os

# Edite à vontade. Quanto mais fontes independentes por categoria, melhor o cruzamento.
FEEDS = {
    "politica": [
        ("g1", "https://g1.globo.com/rss/g1/politica/"),
        ("Folha", "https://feeds.folha.uol.com.br/poder/rss091.xml"),
        ("CNN Brasil", "https://www.cnnbrasil.com.br/politica/feed/"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml"),
    ],
    "economia": [
        ("g1", "https://g1.globo.com/rss/g1/economia/"),
        ("Folha", "https://feeds.folha.uol.com.br/mercado/rss091.xml"),
        ("InfoMoney", "https://www.infomoney.com.br/feed/"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml"),
    ],
    "esportes": [
        ("ge", "https://ge.globo.com/rss/ge/"),
        ("UOL Esporte", "https://rss.uol.com.br/feed/esporte.xml"),
        ("CNN Brasil", "https://www.cnnbrasil.com.br/esportes/feed/"),
    ],
    "tecnologia": [
        ("g1", "https://g1.globo.com/rss/g1/tecnologia/"),
        ("Tecmundo", "https://rss.tecmundo.com.br/feed"),
        ("Olhar Digital", "https://olhardigital.com.br/feed/"),
        ("Canaltech", "https://canaltech.com.br/rss/"),
    ],
    "games": [
        ("Voxel", "https://www.tecmundo.com.br/voxel/rss"),
        ("IGN Brasil", "https://br.ign.com/feed.xml"),
        ("The Enemy", "https://www.theenemy.com.br/rss"),
    ],
}

CATEGORY_LABELS = {
    "politica": "Política",
    "economia": "Economia",
    "esportes": "Esportes",
    "tecnologia": "Tecnologia",
    "games": "Games",
}

MODEL = os.getenv("NF_MODEL", "claude-sonnet-5-5")
DB_PATH = os.getenv("NF_DB", "noticias.db")

# Similaridade mínima (0–1) para duas matérias serem consideradas o mesmo acontecimento.
CLUSTER_THRESHOLD = float(os.getenv("NF_CLUSTER_THRESHOLD", "0.3"))
# Um fato só é publicado se confirmado por pelo menos N fontes diferentes.
MIN_SOURCES = int(os.getenv("NF_MIN_SOURCES", "2"))
# Só considera matérias das últimas N horas.
MAX_AGE_HOURS = int(os.getenv("NF_MAX_AGE_HOURS", "36"))
