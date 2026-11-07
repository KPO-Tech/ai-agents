# invoice-agent

Un agent IA minimal qui trie des factures : **un modèle, des outils limités, des règles**.
Projet de la vidéo « Créer un agent IA de zéro » (chaîne KPO-TECH). Toutes les factures sont imaginaires.

Aucune dépendance en dehors de la bibliothèque standard Python (3.11 ou plus). `pytest` n'est utile que pour les tests.

## Structure

```
src/invoice_agent/
├── loop.py          # la boucle : décider, agir, observer
├── llm.py           # l'interface Model (un vrai modèle ou un faux)
├── fake_model.py    # faux modèle à règles, pour développer sans clé (ce n'est pas de l'IA)
├── zai_model.py     # un vrai modèle : API Z.ai (GLM), sans dépendance
├── tools/           # les seuls outils que l'agent possède
├── guardrails.py    # les règles : chemins, seuil de validation humaine
├── parsing.py       # lecture du montant dans la facture (source de vérité)
├── audit.py         # le journal JSONL de chaque action
├── config.py        # limites : étapes max, seuil, catégories
└── cli.py
data/inbox/          # les factures (texte, imaginaires)
logs/captures/       # vraies sorties du modèle montrées dans la vidéo
tests/
```

## Installer et tester

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate    |    Linux / macOS : source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Lancer

Sans clé, avec le faux modèle :

```bash
python -m invoice_agent --approve ask
```

Avec un vrai modèle (clé Z.ai dans la variable `ZHIPUAI_API_KEY`, ou dans un fichier `.env` à passer avec `--env-file`) :

```bash
python -m invoice_agent --model zai --env-file .env --approve ask -v
```

- `--approve ask|yes|no` : réponse aux demandes de validation humaine (factures au-dessus de 500 EUR).
- `-v` : affiche chaque étape.
- Le résultat est écrit dans `data/output/ledger.json`, le journal dans `logs/`.

## Règles de sécurité

- Le modèle n'a accès qu'aux trois outils enregistrés (`tools/invoices.py`).
- Les fichiers lus restent dans `data/inbox/` (pas de `../`).
- Les arguments sont vérifiés **avant** de déranger un humain.
- Le montant annoncé par le modèle est comparé à celui de la facture : s'ils diffèrent, l'action est refusée.
- Une facture au-dessus du seuil n'est classée qu'après validation humaine.
- Limite d'étapes : l'agent s'arrête, il ne tourne pas à l'infini.
- Un montant illisible est signalé, jamais deviné.

## Ce que le vrai modèle a montré

Deux sorties réelles sont dans `logs/captures/` :

- `run-zai-contournement.txt` : avant correction, après un refus humain pour 1 850 EUR, le modèle a redéclaré la même facture à 24,50 EUR et a passé sous le seuil.
- `run-zai-apres-correction.txt` : après correction, le montant est comparé à la facture, et une faute de frappe sur un nom de fichier est rejetée sans déranger l'humain.

Un agent bien cadré réduit les risques, il ne les supprime pas : garde un humain pour les actions importantes.
