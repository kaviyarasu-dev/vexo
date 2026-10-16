"""Unit tests for export file sanitization and licensing metadata attachment.
Adheres strictly to Phase 19 test plan.
"""

import tempfile
from pathlib import Path
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from core.security import verify_export_metadata, attach_export_metadata_to_file, get_export_metadata


def test_verify_export_metadata_dict():
    valid_meta = {
        "source": "Fyers API",
        "license": "Personal Non-Commercial",
        "disclaimer": "Educational and research purposes only",
    }
    assert verify_export_metadata(valid_meta) is True

    invalid_meta = {
        "source": "Fyers API",
        "license": "Commercial Enterprise Redistribution",
    }
    assert verify_export_metadata(invalid_meta) is False

    empty_meta = {}
    assert verify_export_metadata(empty_meta) is False


def test_attach_and_verify_csv_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_file = Path(tmpdir) / "test_export.csv"
        df = pd.DataFrame({
            "timestamp": ["2026-10-10 09:15:00", "2026-10-10 09:16:00"],
            "open": [2500.0, 2505.0],
            "close": [2504.0, 2510.0],
        })
        df.to_csv(csv_file, index=False)

        # Attach metadata
        attach_export_metadata_to_file(str(csv_file), "csv")

        # Verify file verification returns True
        assert verify_export_metadata(csv_file) is True

        # Read back raw text
        content = csv_file.read_text(encoding="utf-8")
        assert "Personal Non-Commercial" in content
        assert "Fyers API" in content
        assert "SEBI" in content or "disclaimer" in content.lower()


def test_attach_and_verify_parquet_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        parquet_file = Path(tmpdir) / "test_export.parquet"
        df = pd.DataFrame({
            "timestamp": ["2026-10-10 09:15:00", "2026-10-10 09:16:00"],
            "close": [2504.0, 2510.0],
        })
        table = pa.Table.from_pandas(df)
        pq.write_table(table, str(parquet_file))

        # Attach metadata
        attach_export_metadata_to_file(str(parquet_file), "parquet")

        # Verify file metadata passes verification
        assert verify_export_metadata(parquet_file) is True

        # Check metadata directly
        with pq.ParquetFile(str(parquet_file)) as pq_file:
            meta = pq_file.schema_arrow.metadata
            assert b"license" in meta or b"Personal Non-Commercial" in meta.get(b"license", b"")
            assert b"source" in meta
            assert meta[b"source"] == b"Fyers API"
