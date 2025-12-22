#!/usr/bin/env python3
"""Convert MITRE ATT&CK STIX JSON into a sqlite database (tactics/techniques)."""
from __future__ import annotations

import argparse
import json
import sqlite3
from typing import Dict, Iterable, List, Optional, Tuple


def load_objects(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data.get("objects", [])


def get_attack_id(obj: dict) -> Optional[str]:
    for ref in obj.get("external_references", []) or []:
        if ref.get("source_name") == "mitre-attack" and ref.get("external_id"):
            return ref["external_id"]
    return None


def extract_tactics(objects: Iterable[dict]) -> Dict[str, dict]:
    tactics = {}
    for obj in objects:
        if obj.get("type") != "x-mitre-tactic":
            continue
        attack_id = get_attack_id(obj)
        if not attack_id:
            continue
        shortname = obj.get("x_mitre_shortname", attack_id)
        tactics[shortname] = {
            "tactic_id": attack_id,
            "name": obj.get("name", attack_id),
            "shortname": shortname,
        }
    return tactics


def extract_techniques(objects: Iterable[dict]) -> Tuple[List[dict], List[Tuple[str, str]]]:
    techniques: List[dict] = []
    technique_tactics: List[Tuple[str, str]] = []
    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue
        attack_id = get_attack_id(obj)
        if not attack_id:
            continue
        techniques.append({
            "technique_id": attack_id,
            "name": obj.get("name", attack_id),
            "description": obj.get("description", ""),
        })
        for phase in obj.get("kill_chain_phases", []) or []:
            if phase.get("kill_chain_name") != "mitre-attack":
                continue
            phase_name = phase.get("phase_name")
            if phase_name:
                technique_tactics.append((attack_id, phase_name))
    return techniques, technique_tactics


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tactics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tactic_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            shortname TEXT NOT NULL UNIQUE,
            order_index INTEGER NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS techniques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            technique_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tactic_techniques (
            tactic_id TEXT NOT NULL,
            technique_id TEXT NOT NULL,
            PRIMARY KEY (tactic_id, technique_id)
        )
        """
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/enterprise-attack-v18.1.json",
        help="Path to enterprise-attack.json",
    )
    parser.add_argument(
        "--db",
        default="data/mitre_attack.db",
        help="Output sqlite DB path",
    )
    args = parser.parse_args()

    objects = load_objects(args.input)
    tactics = extract_tactics(objects)
    techniques, technique_tactics = extract_techniques(objects)

    conn = sqlite3.connect(args.db)
    init_db(conn)
    cur = conn.cursor()

    cur.execute("DELETE FROM tactic_techniques")
    cur.execute("DELETE FROM tactics")
    cur.execute("DELETE FROM techniques")

    tactic_order = {
        "TA0043": 1,
        "TA0042": 2,
        "TA0001": 3,
        "TA0002": 4,
        "TA0003": 5,
        "TA0004": 6,
        "TA0005": 7,
        "TA0006": 8,
        "TA0007": 9,
        "TA0008": 10,
        "TA0009": 11,
        "TA0011": 12,
        "TA0010": 13,
        "TA0040": 14,
    }

    cur.executemany(
        "INSERT INTO tactics (tactic_id, name, shortname, order_index) VALUES (?, ?, ?, ?)",
        [
            (
                item["tactic_id"],
                item["name"],
                item["shortname"],
                tactic_order.get(item["tactic_id"], 999),
            )
            for item in tactics.values()
        ],
    )
    cur.executemany(
        "INSERT INTO techniques (technique_id, name, description) VALUES (?, ?, ?)",
        [(t["technique_id"], t["name"], t["description"]) for t in techniques],
    )
    tactic_by_shortname = {
        item["shortname"]: item["tactic_id"] for item in tactics.values()
    }
    cur.executemany(
        "INSERT OR IGNORE INTO tactic_techniques (tactic_id, technique_id) VALUES (?, ?)",
        [
            (tactic_by_shortname.get(shortname), technique_id)
            for technique_id, shortname in technique_tactics
            if tactic_by_shortname.get(shortname)
        ],
    )
    conn.commit()
    conn.close()
    print(f"Wrote {len(tactics)} tactics, {len(techniques)} techniques to {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
