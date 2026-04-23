"""Story 1.4 AC-5 Task 5.5 — Prometheus rule file shape tests.

Prometheus itself is installed in Story 1.9; here we verify only that the
rule YAML parses and encodes the LoggerSyncLagHigh alert as specified.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

RULES_FILE = (
    Path(__file__).resolve().parents[2]
    / "infra"
    / "prometheus"
    / "rules"
    / "data_pipeline.rules.yml"
)


def test_rules_file_is_valid_yaml() -> None:
    doc = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    assert "groups" in doc


def test_one_group_one_rule() -> None:
    doc = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    groups = doc["groups"]
    assert len(groups) == 1
    assert groups[0]["name"] == "athena_data_pipeline"
    assert len(groups[0]["rules"]) == 1


def test_logger_sync_lag_high_alert_shape() -> None:
    doc = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    rule = doc["groups"][0]["rules"][0]
    assert rule["alert"] == "LoggerSyncLagHigh"
    # 120s threshold is the NFR-O2 SLO
    assert "time() - athena_logger_sync_last_success_seconds > 120" in rule["expr"]
    assert rule["for"] == "30s"
    assert rule["labels"]["severity"] == "high"
    assert "summary" in rule["annotations"]
    assert "description" in rule["annotations"]


def test_alert_guards_against_missing_metric_series() -> None:
    """Review-flip fix: without an `absent()` disjunct, a missing metric
    series (e.g. emitter never ran post-reboot because venv path broke)
    evaluates to no-data and the alert never fires — the worst failure
    mode becomes invisible. The `absent()` branch fires immediately in
    that case."""
    doc = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    rule = doc["groups"][0]["rules"][0]
    assert "absent(athena_logger_sync_last_success_seconds)" in rule["expr"]
