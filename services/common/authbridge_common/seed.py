"""Loads the synthetic seed data in shared/seed (mock mode and SQL generation)."""

import json
from pathlib import Path


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_seed(seed_dir):
    seed_dir = Path(seed_dir)
    ehr = load_json(seed_dir / "ehr.json")
    payer = load_json(seed_dir / "payer.json")
    questionnaires = {}
    for p in sorted((seed_dir / "questionnaires").glob("*.json")):
        q = load_json(p)
        questionnaires[q["id"]] = q
    policies = {}
    for p in sorted((seed_dir / "policies").glob("*.md")):
        policies[p.stem] = p.read_text(encoding="utf-8")
    return {"ehr": ehr, "payer": payer, "questionnaires": questionnaires, "policies": policies}


def policy_sections(policy_id, markdown):
    """Split a policy markdown file into citable sections keyed by section id
    (the token after the '#'s, e.g. 'MRI-3.2')."""
    sections = []
    current = None
    for line in markdown.splitlines():
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            token = heading.split(" ")[0]
            if current:
                sections.append(current)
            sid = token if any(ch.isdigit() for ch in token) else policy_id
            current = {"policy_doc_id": policy_id, "section_id": sid, "section_title": heading, "text": ""}
        elif current is not None:
            current["text"] += line + "\n"
    if current:
        sections.append(current)
    for s in sections:
        s["text"] = s["text"].strip()
    return [s for s in sections if s["text"]]
