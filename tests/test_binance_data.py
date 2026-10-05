import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import binance_data


class _Response(BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class BinanceDataTests(unittest.TestCase):
    def test_rejects_invalid_month(self) -> None:
        with self.assertRaises(ValueError):
            binance_data.download_binance_data("trades", "BTCUSDT", "2026-13")

    def test_single_month_download_saves_zip(self) -> None:
        payload = b"zip-content"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(
                binance_data,
                "_download_file",
                side_effect=lambda _url, path: path.write_bytes(payload),
            ) as download:
                paths = binance_data.download_binance_data(
                    "trades",
                    "BTCUSDT",
                    "2026-08",
                    temporary_directory,
                )

            self.assertEqual(len(paths), 1)
            self.assertEqual(paths[0].name, "BTCUSDT-trades-2026-08.zip")
            self.assertEqual(paths[0].read_bytes(), payload)
            download.assert_called_once_with(
                "https://data.binance.vision/data/spot/monthly/trades/"
                "BTCUSDT/BTCUSDT-trades-2026-08.zip",
                paths[0],
            )

    def test_rejects_path_segments(self) -> None:
        with self.assertRaises(ValueError):
            binance_data.download_binance_data("../trades", "BTCUSDT", "2026-08")

    def test_klines_requires_supported_candle_size(self) -> None:
        with self.assertRaisesRegex(ValueError, "candle_size é obrigatório"):
            binance_data.download_binance_data("klines", "BTCUSDT", "2026-08")

        with self.assertRaisesRegex(ValueError, "candle_size inválido"):
            binance_data.download_binance_data(
                "klines", "BTCUSDT", "2026-08", candle_size="7m"
            )

    def test_single_month_klines_uses_binance_interval_path_and_filename(self) -> None:
        payload = b"zip-content"
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(
                binance_data,
                "_download_file",
                side_effect=lambda _url, path: path.write_bytes(payload),
            ) as download:
                paths = binance_data.download_binance_data(
                    "klines",
                    "BTCUSDT",
                    "2026-08",
                    temporary_directory,
                    candle_size="1m",
                )

            self.assertEqual(paths[0].name, "BTCUSDT-1m-2026-08.zip")
            download.assert_called_once_with(
                "https://data.binance.vision/data/spot/monthly/klines/"
                "BTCUSDT/1m/BTCUSDT-1m-2026-08.zip",
                paths[0],
            )

    def test_all_klines_lists_only_the_selected_interval(self) -> None:
        key = (
            "data/spot/monthly/klines/BTCUSDT/1h/"
            "BTCUSDT-1h-2026-08.zip"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.object(binance_data, "_monthly_zip_keys", return_value=[key]) as listing,
                patch.object(
                    binance_data,
                    "_download_file",
                    side_effect=lambda _url, path: path.write_bytes(b"zip-content"),
                ),
            ):
                paths = binance_data.download_binance_data(
                    "klines",
                    "BTCUSDT",
                    url_destino=temporary_directory,
                    candle_size="1h",
                )

        listing.assert_called_once_with("data/spot/monthly/klines/BTCUSDT/1h/")
        self.assertEqual(paths[0].name, "BTCUSDT-1h-2026-08.zip")

    def test_candle_size_is_not_valid_for_other_data_types(self) -> None:
        with self.assertRaisesRegex(ValueError, "só deve ser informado"):
            binance_data.download_binance_data(
                "trades", "BTCUSDT", "2026-08", candle_size="1m"
            )

    def test_lists_monthly_zip_files_and_skips_checksums(self) -> None:
        first_page = b"""<?xml version="1.0"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
          <IsTruncated>true</IsTruncated>
          <NextContinuationToken>next-page</NextContinuationToken>
          <Contents><Key>data/spot/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-07.zip</Key></Contents>
          <Contents><Key>data/spot/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-07.zip.CHECKSUM</Key></Contents>
        </ListBucketResult>"""
        second_page = b"""<?xml version="1.0"?>
        <ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
          <IsTruncated>false</IsTruncated>
          <Contents><Key>data/spot/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-08.zip</Key></Contents>
        </ListBucketResult>"""
        responses = [_Response(first_page), _Response(second_page)]

        with patch.object(
            binance_data.urllib.request,
            "urlopen",
            side_effect=responses,
        ) as urlopen:
            keys = binance_data._monthly_zip_keys(
                "data/spot/monthly/trades/BTCUSDT/"
            )

        self.assertEqual(
            keys,
            [
                "data/spot/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-07.zip",
                "data/spot/monthly/trades/BTCUSDT/BTCUSDT-trades-2026-08.zip",
            ],
        )
        self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
