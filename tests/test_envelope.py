"""Envelope model shape and validation."""
import pytest
from pydantic import ValidationError

from tools.envelope import Artifact, ToolResult


def test_artifact_fields():
    a = Artifact(path_hint="ohlcv.csv", media_type="text/csv", content="Date,Close\n2024-01-01,180")
    assert a.path_hint == "ohlcv.csv"
    assert a.media_type == "text/csv"
    assert "Date" in a.content


def test_tool_result_model_dump():
    result = ToolResult(
        summary="AAPL OHLCV — 5 rows",
        artifacts=[
            Artifact(path_hint="ohlcv.csv", media_type="text/csv", content="a,b\n1,2")
        ],
    )
    d = result.model_dump()
    assert d["summary"] == "AAPL OHLCV — 5 rows"
    assert len(d["artifacts"]) == 1
    assert d["artifacts"][0]["path_hint"] == "ohlcv.csv"


def test_tool_result_empty_artifacts():
    result = ToolResult(summary="no data", artifacts=[])
    assert result.model_dump()["artifacts"] == []


def test_artifact_requires_all_fields():
    with pytest.raises(ValidationError):
        Artifact(path_hint="x.csv", media_type="text/csv")  # missing content
