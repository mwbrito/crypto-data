# crypto-data

## Download de dados da Binance

O módulo `binance_data.py` baixa arquivos ZIP mensais do Binance Vision. Use
`data="YYYY-MM"` para baixar um mês específico ou `data=None` para listar e
baixar todos os meses disponíveis para o ticker e tipo de arquivo. O argumento
`url_destino` é o diretório local onde os arquivos serão salvos.

```python
from binance_data import download_binance_data

arquivos = download_binance_data(
    tipo_arquivo="trades",
    ticker="BTCUSDT",
    data="2026-08",
    url_destino="downloads",
)
```

Baixar todos os arquivos de `trades` pode consumir bastante espaço e banda.
O notebook `analise_dados_binance.ipynb` demonstra a chamada do módulo com um
único mês. Para executar as células de análise e visualização, instale
`pandas` e `matplotlib` com `python -m pip install pandas matplotlib`.

Para `klines`, informe também `candle_size`. O intervalo é incluído no caminho
e no nome do arquivo conforme o formato da Binance:

```python
arquivos = download_binance_data(
    tipo_arquivo="klines",
    ticker="BTCUSDT",
    data="2026-08",
    url_destino="downloads",
    candle_size="1m",
)
```

Isso busca `data/spot/monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-08.zip`.
Intervalos aceitos incluem `1s`, `1m`, `5m`, `1h`, `1d` e `1mo`.