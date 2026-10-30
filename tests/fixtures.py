from app.models import Article

SELIC = [
    Article("g1", "economia", "Copom mantém Selic em 15% ao ano",
            "O Comitê de Política Monetária do Banco Central decidiu nesta quarta-feira manter a taxa básica de juros em 15% ao ano. A decisão foi unânime. Analistas veem a medida como dura demais.",
            "https://g1.example/selic"),
    Article("Folha", "economia", "Banco Central mantém juros em 15% pela quarta vez seguida",
            "O Copom manteve a Selic em 15% ao ano nesta quarta-feira, em decisão unânime. É a quarta manutenção seguida. Para economistas, o BC erra ao não cortar.",
            "https://folha.example/selic"),
    Article("InfoMoney", "economia", "Selic fica em 15%; Copom sinaliza cautela",
            "O Copom decidiu manter a Selic em 15% ao ano. Em comunicado, o comitê afirmou que seguirá vigilante. O mercado esperava a manutenção.",
            "https://infomoney.example/selic"),
]
OUTRO = Article("g1", "economia", "Petrobras anuncia reajuste da gasolina nas refinarias",
                "A Petrobras anunciou reajuste de 4% no preço da gasolina vendida às distribuidoras.",
                "https://g1.example/petro")
