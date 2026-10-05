"""Download monthly market-data ZIP files from Binance Vision."""

from __future__ import annotations

import re
import shutil
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

_BUCKET_LIST_URL = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/"
_DOWNLOAD_BASE_URL = "https://data.binance.vision/"
_TIMEOUT_SECONDS = 60
_MONTH_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_PATH_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_KLINE_INTERVALS = {
    "1s",
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1mo",
}


def _validate_segment(value: str, name: str) -> str:
    if not isinstance(value, str) or not _PATH_SEGMENT_PATTERN.fullmatch(value):
        raise ValueError(f"{name} deve conter apenas letras, números, '_' ou '-'.")
    return value


def _monthly_zip_keys(prefix: str) -> list[str]:
    keys: list[str] = []
    continuation_token: str | None = None

    while True:
        params = {"list-type": "2", "prefix": prefix}
        if continuation_token is not None:
            params["continuation-token"] = continuation_token
        listing_url = f"{_BUCKET_LIST_URL}?{urllib.parse.urlencode(params)}"

        with urllib.request.urlopen(
            listing_url, timeout=_TIMEOUT_SECONDS
        ) as response:
            root = ET.fromstring(response.read())

        for item in root.findall(".//{*}Contents"):
            key_element = item.find("{*}Key")
            if key_element is not None and key_element.text:
                key = key_element.text
                if key.startswith(prefix) and key.endswith(".zip"):
                    keys.append(key)

        truncated = root.findtext(".//{*}IsTruncated", default="false")
        if truncated.lower() != "true":
            break

        continuation_token = root.findtext(".//{*}NextContinuationToken")
        if not continuation_token:
            raise RuntimeError(
                "A listagem da Binance indicou mais resultados, "
                "mas não retornou o token de paginação."
            )

    return keys


def _download_file(url: str, destination: Path) -> None:
    temporary_path = destination.with_name(f"{destination.name}.part")
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT_SECONDS) as response:
            with temporary_path.open("wb") as output:
                shutil.copyfileobj(response, output)
        temporary_path.replace(destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def download_binance_data(
    tipo_arquivo: str,
    ticker: str,
    data: str | None = None,
    url_destino: str | Path = "downloads",
    candle_size: str | None = None,
) -> list[Path]:
    """Download monthly ZIPs from Binance Vision.

    Args:
        tipo_arquivo: Binance dataset name, such as ``trades``, ``aggTrades``
            or ``klines``.
        ticker: Market symbol, such as ``BTCUSDT``.
        data: Month as ``YYYY-MM`` to download one ZIP, or ``None`` to
            download all monthly ZIPs available for the market and dataset.
        url_destino: Local directory in which ZIPs are saved.
        candle_size: Required kline interval, such as ``1m`` or ``1h``.
            Must be omitted for other dataset types.

    Returns:
        Paths to downloaded or already-present ZIP files.

    Raises:
        ValueError: If an input does not match the expected format.
        urllib.error.URLError: If Binance cannot be reached or a download fails.
    """
    tipo_arquivo = _validate_segment(tipo_arquivo, "tipo_arquivo")
    ticker = _validate_segment(ticker, "ticker")
    if tipo_arquivo == "klines":
        if candle_size is None:
            raise ValueError("candle_size é obrigatório quando tipo_arquivo='klines'.")
        candle_size = _validate_segment(candle_size, "candle_size")
        if candle_size not in _KLINE_INTERVALS:
            raise ValueError(
                "candle_size inválido. Use um intervalo suportado pela Binance, "
                "como '1m', '1h' ou '1d'."
            )
    elif candle_size is not None:
        raise ValueError("candle_size só deve ser informado para tipo_arquivo='klines'.")

    if data is not None and (
        not isinstance(data, str) or not _MONTH_PATTERN.fullmatch(data)
    ):
        raise ValueError("data deve estar no formato YYYY-MM ou ser None.")

    prefix = f"data/spot/monthly/{tipo_arquivo}/{ticker}/"
    if tipo_arquivo == "klines":
        prefix = f"{prefix}{candle_size}/"
    if data is None:
        keys = _monthly_zip_keys(prefix)
    else:
        if tipo_arquivo == "klines":
            filename = f"{ticker}-{candle_size}-{data}.zip"
        else:
            filename = f"{ticker}-{tipo_arquivo}-{data}.zip"
        keys = [f"{prefix}{filename}"]

    destination_directory = Path(url_destino).expanduser()
    destination_directory.mkdir(parents=True, exist_ok=True)
    downloaded_paths: list[Path] = []

    for key in keys:
        file_path = destination_directory / Path(key).name
        if not file_path.exists():
            file_url = urllib.parse.urljoin(_DOWNLOAD_BASE_URL, key)
            _download_file(file_url, file_path)
        downloaded_paths.append(file_path)

    if not downloaded_paths:
        raise FileNotFoundError(
            f"Nenhum arquivo mensal encontrado para {ticker}/{tipo_arquivo}."
        )

    return downloaded_paths
