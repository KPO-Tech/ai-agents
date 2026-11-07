import json
from dataclasses import replace

import pytest

from invoice_agent.audit import AuditLog
from invoice_agent.config import Settings
from invoice_agent.fake_model import FakeModel
from invoice_agent.parsing import parse_amount
from invoice_agent.guardrails import approve_all, deny_all, safe_inbox_path
from invoice_agent.llm import Final, ScriptedModel, ToolCall
from invoice_agent.loop import run_agent
from invoice_agent.errors import ToolError
from invoice_agent.tools import build_registry

INVOICES = {
    "facture_001.txt": "Fournisseur : Électricité Lumina\nTotal TTC : 142,80 EUR\n",
    "facture_002.txt": "Fournisseur : Papeterie Dupont\nTotal TTC : 36,40 EUR\n",
    "facture_003.txt": "Fournisseur : Cabinet Martin Conseil\nTotal TTC : 1 850,00 EUR\n",
    "facture_005.txt": "Montant : illisible (scan abîmé)\n",
}


@pytest.fixture
def settings(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    for name, text in INVOICES.items():
        (inbox / name).write_text(text, encoding="utf-8")
    return Settings(inbox=inbox, output=tmp_path / "out", logs=tmp_path / "logs")


def run(settings, model, approve=deny_all):
    return run_agent(
        model, build_registry(settings), "trie", settings, AuditLog(settings.logs, "t"), approve
    )


def ledger(settings):
    return {r["name"]: r for r in json.loads((settings.output / "ledger.json").read_text(encoding="utf-8"))}


def test_parse_amount_handles_french_formats():
    assert parse_amount("Total TTC : 1 850,00 EUR") == 1850.0
    assert parse_amount("Total TTC : 142,80 EUR") == 142.8
    assert parse_amount("Montant : illisible") is None


def test_fake_model_sorts_small_invoices_and_flags_unreadable(settings):
    result = run(settings, FakeModel(), approve=deny_all)
    assert result.status == "done"
    rows = ledger(settings)
    assert rows["facture_001.txt"]["category"] == "energie"
    assert rows["facture_002.txt"]["category"] == "fournitures"
    assert "facture_003.txt" not in rows  # refusée par l'humain
    assert "facture_005.txt" not in rows  # illisible : jamais devinée
    assert "facture_005.txt" in result.final


def test_human_approval_lets_large_invoice_through(settings):
    run(settings, FakeModel(), approve=approve_all)
    assert ledger(settings)["facture_003.txt"]["amount"] == 1850.0


def test_step_limit_stops_a_runaway_model(settings):
    settings = replace(settings, max_steps=3)
    loop_forever = ScriptedModel([ToolCall(f"c{i}", "list_invoices", {}) for i in range(10)])
    result = run(settings, loop_forever)
    assert result.status == "step_limit"
    assert result.steps == 3


def test_unknown_tool_becomes_an_observation_not_a_crash(settings):
    model = ScriptedModel([ToolCall("c1", "delete_everything", {}), Final("fini")])
    assert run(settings, model).status == "done"
    log = (settings.logs / "t.jsonl").read_text(encoding="utf-8")
    assert "outil inconnu" in log


def test_path_traversal_is_blocked(settings):
    with pytest.raises(ToolError):
        safe_inbox_path(settings, "../secret.txt")
    with pytest.raises(ToolError):
        safe_inbox_path(settings, "absent.txt")


def test_invalid_category_is_rejected(settings):
    registry = build_registry(settings)
    with pytest.raises(ToolError):
        registry.call("classify_invoice", {"name": "facture_001.txt", "category": "yachts", "amount": 10})


def test_human_is_not_asked_about_an_invalid_call(settings):
    asked = []

    def spy(call):
        asked.append(call)
        return True

    typo = ToolCall("c1", "classify_invoice", {"name": "facture_03.txt", "category": "prestations", "amount": 1850.0})
    result = run(settings, ScriptedModel([typo, Final("fini")]), approve=spy)
    assert result.status == "done"
    assert asked == []  # le fichier n'existe pas : aucun humain dérangé
    assert "introuvable" in (settings.logs / "t.jsonl").read_text(encoding="utf-8")


def test_model_cannot_dodge_approval_by_lowering_the_amount(settings):
    """Cas réel observé : après un refus, le modèle a redéclaré 24,50 EUR au lieu de 1 850 EUR."""
    lie = ToolCall("c1", "classify_invoice", {"name": "facture_003.txt", "category": "restauration", "amount": 24.5})
    asked = []
    result = run(settings, ScriptedModel([lie, Final("fini")]), approve=lambda c: asked.append(c) or True)
    assert result.status == "done"
    assert not (settings.output / "ledger.json").exists()  # rien d'enregistré
    assert "incohérent" in (settings.logs / "t.jsonl").read_text(encoding="utf-8")


def test_audit_log_records_every_step(settings):
    run(settings, FakeModel(), approve=deny_all)
    events = [json.loads(line)["event"] for line in (settings.logs / "t.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[0] == "start" and events[-1] == "final"
    assert "approval" in events
