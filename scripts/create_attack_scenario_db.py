#!/usr/bin/env python3
"""Create an attack scenario sqlite database with scenario and step tables."""
from __future__ import annotations

import argparse
import sqlite3


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attack_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS attack_scenario_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenairo_id INTEGER NOT NULL,
            "order" INTEGER NOT NULL,
            technquename TEXT NOT NULL,
            FOREIGN KEY (scenairo_id) REFERENCES attack_scenarios(id)
        )
        """
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--db",
        default="data/attack_scenario.db",
        help="Output sqlite DB path",
    )
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    init_db(conn)
    cur = conn.cursor()

    cur.execute("INSERT INTO attack_scenarios (name) VALUES (?)", ("sample scenario",))
    scenario_id = cur.lastrowid
    steps = [
        "T1190",
        "T1021.002",
        "T1003.001",
        "T1021.001",
        "T1041",
    ]
    cur.executemany(
        'INSERT INTO attack_scenario_steps (scenairo_id, "order", technquename) VALUES (?, ?, ?)',
        [(scenario_id, idx + 1, technique) for idx, technique in enumerate(steps)],
    )
    conn.commit()
    conn.close()
    print(f"Created sqlite DB at {args.db}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
