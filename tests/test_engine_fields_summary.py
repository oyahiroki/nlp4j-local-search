"""Integration test for SearchEngine.fields_summary().

Requires the JVM and a JAR that exposes LocalSearch.getFieldsSummary().
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nlp4j_local_search import SearchEngine


def test_engine_fields_summary():

    with SearchEngine(
        "en",
        auto_analyze=False,
    ) as engine:

        engine.add_json({
            "id": "1",
            "text": "hello",
            "maker_s": "NISSAN",
            "model_year_i": 2024,
        })

        engine.add_json({
            "id": "2",
            "text": "world",
            "maker_s": "NISSAN",
        })

        engine.add_json({
            "id": "3",
            "text": "test",
            "maker_s": "TOYOTA",
            "model_year_i": 2025,
        })

        engine.commit()

        summary = engine.fields_summary()

        assert summary.document_count == 3

        by_name = {
            field.field: field
            for field in summary.fields
        }

        maker = by_name["maker_s"]

        assert maker.kind == "KEYWORD"
        assert maker.aggregatable is True
        assert maker.coverage == 1.0
        assert maker.unique_count == 2

        year = by_name["model_year_i"]

        assert year.kind == "INTEGER"
        assert year.aggregatable is True

        assert year.coverage == pytest.approx(
            2 / 3
        )

        assert year.unique_count is None
        assert year.diversity is None
