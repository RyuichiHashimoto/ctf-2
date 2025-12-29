#!/usr/bin/env python3
"""Migrate MITRE ATT&CK data from sqlite to MySQL."""
from __future__ import annotations

import argparse
import sqlite3

import mysql.connector


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sqlite", default="data/mitre_attack.db")
    parser.add_argument("--mysql-host", default="127.0.0.1")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-db", default="mitre_attack")
    parser.add_argument("--mysql-user", default="mitre_user")
    parser.add_argument("--mysql-pass", default="mitre_pass")
    args = parser.parse_args()

    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_conn.row_factory = sqlite3.Row

    mysql_conn = mysql.connector.connect(
        host=args.mysql_host,
        port=args.mysql_port,
        user=args.mysql_user,
        password=args.mysql_pass,
        database=args.mysql_db,
    )
    mysql_cur = mysql_conn.cursor()

    mysql_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tactics (
            id INT AUTO_INCREMENT PRIMARY KEY,
            tactic_id VARCHAR(32) NOT NULL UNIQUE,
            name TEXT NOT NULL,
            shortname TEXT NOT NULL UNIQUE,
            order_index INT NOT NULL
        )
        """
    )
    mysql_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS techniques (
            id INT AUTO_INCREMENT PRIMARY KEY,
            technique_id VARCHAR(32) NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description MEDIUMTEXT NOT NULL
        )
        """
    )
    mysql_cur.execute(
        """
        CREATE TABLE IF NOT EXISTS tactic_techniques (
            tactic_id VARCHAR(32) NOT NULL,
            technique_id VARCHAR(32) NOT NULL,
            PRIMARY KEY (tactic_id, technique_id)
        )
        """
    )

    mysql_cur.execute("DELETE FROM tactic_techniques")
    mysql_cur.execute("DELETE FROM tactics")
    mysql_cur.execute("DELETE FROM techniques")

    sqlite_cur = sqlite_conn.cursor()

    tactics = sqlite_cur.execute(
        "SELECT tactic_id, name, shortname, order_index FROM tactics"
    ).fetchall()
    mysql_cur.executemany(
        "INSERT INTO tactics (tactic_id, name, shortname, order_index) VALUES (%s, %s, %s, %s)",
        [(row["tactic_id"], row["name"], row["shortname"], row["order_index"]) for row in tactics],
    )

    techniques = sqlite_cur.execute(
        "SELECT technique_id, name, description FROM techniques"
    ).fetchall()
    mysql_cur.executemany(
        "INSERT INTO techniques (technique_id, name, description) VALUES (%s, %s, %s)",
        [(row["technique_id"], row["name"], row["description"]) for row in techniques],
    )

    links = sqlite_cur.execute(
        "SELECT tactic_id, technique_id FROM tactic_techniques"
    ).fetchall()
    mysql_cur.executemany(
        "INSERT INTO tactic_techniques (tactic_id, technique_id) VALUES (%s, %s)",
        [(row["tactic_id"], row["technique_id"]) for row in links],
    )

    mysql_conn.commit()
    mysql_conn.close()
    sqlite_conn.close()
    print(f"Migrated {len(tactics)} tactics, {len(techniques)} techniques")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
