"""Configuração: fontes RSS por categoria e parâmetros do pipeline."""
import os

# Edite à vontade. Quanto mais fontes independentes por categoria, melhor o cruzamento.
FEEDS = {
    "brasil": [
        ("Folha", "https://feeds.folha.uol.com.br/cotidiano/rss091.xml"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/geral/feed.xml"),
    ],
    "politica": [
        ("g1", "https://g1.globo.com/rss/g1/politica/"),
        ("Folha", "https://feeds.folha.uol.com.br/poder/rss091.xml"),
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
    ],
    "mundo": [
        ("g1", "https://g1.globo.com/rss/g1/mundo/"),
        ("Folha", "https://feeds.folha.uol.com.br/mundo/rss091.xml"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/internacional/feed.xml"),
        ("BBC Brasil", "https://feeds.bbci.co.uk/portuguese/rss.xml"),
    ],
    "saude": [
        ("g1", "https://g1.globo.com/rss/g1/bemestar/"),
        ("Folha", "https://feeds.folha.uol.com.br/equilibrioesaude/rss091.xml"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/saude/feed.xml"),
    ],
    "ciencia": [
        ("Folha", "https://feeds.folha.uol.com.br/ciencia/rss091.xml"),
        ("Olhar Digital", "https://olhardigital.com.br/ciencia-e-espaco/feed/"),
    ],
    "educacao": [
        ("g1", "https://g1.globo.com/rss/g1/educacao/"),
        ("Folha", "https://feeds.folha.uol.com.br/educacao/rss091.xml"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/educacao/feed.xml"),
    ],
    "cultura": [
        ("g1", "https://g1.globo.com/rss/g1/pop-arte/"),
        ("Folha", "https://feeds.folha.uol.com.br/ilustrada/rss091.xml"),
        ("Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/cultura/feed.xml"),
        ("UOL", "https://rss.uol.com.br/feed/entretenimento.xml"),
    ],
    "tecnologia": [
        ("g1", "https://g1.globo.com/rss/g1/tecnologia/"),
        ("Tecmundo", "https://rss.tecmundo.com.br/feed"),
        ("Olhar Digital", "https://olhardigital.com.br/feed/"),
        ("Canaltech", "https://canaltech.com.br/rss/"),
    ],
}

CATEGORY_LABELS = {
    "brasil": "Brasil",
    "politica": "Política",
    "economia": "Economia",
    "esportes": "Esportes",
    "mundo": "Mundo",
    "saude": "Saúde",
    "ciencia": "Ciência",
    "educacao": "Educação",
    "cultura": "Cultura",
    "tecnologia": "Tecnologia",
}

MODEL = os.getenv("NF_MODEL", "claude-sonnet-5-5")
# Modelo pequeno e grátis rodando via Ollama (ex.: "qwen3:4b"). Se definido, é usado no lugar do Claude.
LOCAL_MODEL = os.getenv("NF_MODELO_LOCAL", "")
# Fração mínima das palavras do trecho citado que precisa aparecer na matéria (1 = cópia exata).
QUOTE_MATCH = float(os.getenv("NF_TRECHO_MINIMO", "1"))
# Se um fato só tem trecho de um veículo, procura os números e nomes dele na matéria de outro veículo.
CROSS_CHECK = os.getenv("NF_CRUZAR", "0") == "1"
OLLAMA_URL = os.getenv("NF_OLLAMA_URL", "http://localhost:11434/api/chat")
DB_PATH = os.getenv("NF_DB", "noticias.db")

# Similaridade mínima (0–1) para duas matérias serem consideradas o mesmo acontecimento.
CLUSTER_THRESHOLD = float(os.getenv("NF_CLUSTER_THRESHOLD", "0.3"))
# Um fato só é publicado se confirmado por pelo menos N fontes diferentes.
MIN_SOURCES = int(os.getenv("NF_MIN_SOURCES", "2"))
# Só considera matérias das últimas N horas.
MAX_AGE_HOURS = int(os.getenv("NF_MAX_AGE_HOURS", "36"))
