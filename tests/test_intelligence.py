import json

import pytest

from moxie import TrendOpportunity, research_opportunity


@pytest.fixture
def raw():
    return {
        "opportunity_id": "trend-001",
        "topic": "Rainwater harvesting",
        "audience": "Households",
        "platform": "youtube",
        "observed_at": "2026-11-06T00:00:00Z",
        "signals": ["Two observed discussions about storage sizing"],
        "source_refs": ["internal-sample:001"],
    }


def test_intake_and_research_artifact(raw):
    artifact = research_opportunity(TrendOpportunity.from_mapping(raw))
    assert artifact.opportunity_id == "trend-001"
    assert artifact.observations == tuple(raw["signals"])
    assert artifact.source_refs == tuple(raw["source_refs"])
    assert artifact.evidence_status == "USER_SUPPLIED_UNVERIFIED"
    assert json.loads(json.dumps(artifact.to_dict()))["topic"] == raw["topic"]


def test_deterministic_identity(raw):
    first = research_opportunity(TrendOpportunity.from_mapping(raw))
    second = research_opportunity(TrendOpportunity.from_mapping(dict(raw)))
    assert first == second
    changed = dict(raw, signals=["Different observed discussion"])
    assert first.artifact_id != research_opportunity(TrendOpportunity.from_mapping(changed)).artifact_id


@pytest.mark.parametrize("change", [
    {"topic": ""}, {"signals": []}, {"source_refs": [""]},
    {"unexpected": "field"}, {"observed_at": None},
])
def test_invalid_intake_rejected(raw, change):
    with pytest.raises(ValueError):
        TrendOpportunity.from_mapping(dict(raw, **change))


def test_no_io_or_channel_side_effects(raw, monkeypatch):
    import socket
    import subprocess
    monkeypatch.setattr(socket, "create_connection", lambda *a, **k: (_ for _ in ()).throw(AssertionError("network called")))
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("process called")))
    assert research_opportunity(TrendOpportunity.from_mapping(raw)).artifact_id.startswith("research-")
