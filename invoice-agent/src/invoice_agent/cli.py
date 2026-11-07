from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audit import AuditLog
from .config import Settings
from .envfile import load_env_file
from .fake_model import FakeModel
from .guardrails import approve_all, ask_in_terminal, deny_all
from .llm import Model
from .loop import run_agent
from .tools import build_registry
from .zai_model import DEFAULT_MODEL, ZaiModel

APPROVERS = {"ask": ask_in_terminal, "yes": approve_all, "no": deny_all}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="invoice-agent", description="Trie les factures de data/inbox.")
    p.add_argument("--model", choices=["fake", "zai"], default="fake", help="fake = règles sans réseau ; zai = vrai modèle GLM")
    p.add_argument("--model-name", default=DEFAULT_MODEL, help="nom du modèle Z.ai")
    p.add_argument("--env-file", type=Path, help="fichier .env contenant ZHIPUAI_API_KEY")
    p.add_argument("--approve", choices=list(APPROVERS), default="ask", help="réponse aux demandes de validation")
    p.add_argument("-v", "--verbose", action="store_true", help="afficher chaque étape")
    args = p.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # accents corrects dans le terminal Windows

    if args.env_file:
        load_env_file(args.env_file)
    model: Model = ZaiModel(args.model_name) if args.model == "zai" else FakeModel()

    settings = Settings()
    audit = AuditLog(settings.logs, echo=args.verbose)
    result = run_agent(
        model,
        build_registry(settings),
        "Trie les factures de la boîte de réception.",
        settings,
        audit,
        APPROVERS[args.approve],
    )
    print(f"\n[{result.status}] en {result.steps} étapes\n{result.final}\nJournal : {audit.path}")
    return 0 if result.status == "done" else 1
