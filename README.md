# Só os Fatos — protótipo

Agrega notícias de vários veículos, agrupa as que falam do mesmo acontecimento e publica
só o que pelo menos 2 veículos diferentes noticiaram.

- **Modo grátis** (padrão, sem `ANTHROPIC_API_KEY`): mostra cada acontecimento com a manchete de cada veículo.
- **Modo com IA** (com a chave): o Claude extrai os fatos em linguagem neutra e o código confere as evidências.
  É pago por uso; o workflow do GitHub não usa a chave, então lá roda sempre grátis.

## Como funciona

1. **Coleta** (`app/collect.py`): lê os feeds RSS listados em `app/config.py`, por categoria.
2. **Agrupamento** (`app/cluster.py`): TF-IDF + similaridade de cosseno; junta matérias de veículos
   diferentes sobre o mesmo assunto. Grupos com uma única fonte são ignorados.
3. **Extração** (`app/extract.py`): o Claude recebe o grupo e devolve manchete neutra, fatos e
   divergências. Para cada fato, ele precisa citar o trecho literal de cada matéria que o sustenta.
4. **Verificação anti-alucinação**: o código confere se cada trecho citado existe de verdade na
   matéria. Fato sem evidência real ou com menos de 2 veículos distintos é descartado.
5. **Exibição** (`app/main.py` + `app/static/index.html`): API FastAPI + página com filtro por categoria,
   selo "✓ N fontes" em cada fato, aviso de divergência e links para as matérias originais.

## Rodando

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python demo.py                       # opcional: notícia de exemplo, sem API nem internet
uvicorn app.main:app --reload        # abra http://localhost:8000
python build_site.py                 # gera o site estático em site/ (o que vai para o celular)

export ANTHROPIC_API_KEY=sk-ant-...  # Windows: set ANTHROPIC_API_KEY=...
python pipeline.py --dry-run         # só coleta e agrupa (grátis) — bom para calibrar
python pipeline.py                   # ciclo completo, todas as categorias
python pipeline.py esportes games    # só algumas
```

## App no celular (GitHub)

O workflow `.github/workflows/atualizar.yml` roda no GitHub a cada 2 horas: coleta, extrai os fatos,
guarda o banco em `data/noticias.db` e publica o site no GitHub Pages. O Mac pode ficar desligado.

1. No repositório: **Settings → Secrets and variables → Actions → New repository secret**,
   nome `ANTHROPIC_API_KEY`. Ou no terminal: `gh secret set ANTHROPIC_API_KEY`.
2. **Actions → Atualizar notícias → Run workflow** para a primeira atualização.
3. Abra o link do Pages no celular:
   - iPhone (Safari): Compartilhar → **Adicionar à Tela de Início**.
   - Android (Chrome): menu ⋮ → **Instalar app**.

Para mudar a frequência, edite a linha `cron` do workflow. Grupos já processados não são enviados de
novo ao modelo; quando um acontecimento ganha matérias novas, ele é refeito e substitui a versão antiga.
Notícias com mais de 7 dias são apagadas.

## Ajustes (variáveis de ambiente)

| Variável | Padrão | O que faz |
|---|---|---|
| `NF_MODEL` | `claude-sonnet-5-5` | Modelo usado na extração |
| `NF_CLUSTER_THRESHOLD` | `0.3` | Similaridade para juntar matérias. Subir = grupos mais estritos |
| `NF_MIN_SOURCES` | `2` | Mínimo de veículos que confirmam um fato |
| `NF_MAX_AGE_HOURS` | `36` | Idade máxima das matérias coletadas |
| `NF_DB` | `noticias.db` | Arquivo SQLite |

## Testes

```bash
python -m pytest -q
```

Cobrem: agrupamento, casamento de trechos (acentos, maiúsculas, espaços), descarte de fato
alucinado, descarte de fato com fonte única e contagem de veículos distintos (2 matérias do g1 = 1 fonte).

## Limitações conhecidas

- Os feeds RSS trazem só título e resumo. Isso limita quantos fatos dá para cruzar; o próximo passo
  natural é baixar o texto completo das matérias abertas.
- Algumas URLs de RSS mudam com o tempo. Se uma fonte aparecer com `ERRO`, troque a URL em `config.py`.
- O agrupamento por TF-IDF é simples. Se juntar assuntos diferentes ou separar o mesmo assunto,
  calibre o threshold com `--dry-run` ou troque por embeddings.
- O texto das matérias não é republicado: só os fatos reescritos e o link para o original.
