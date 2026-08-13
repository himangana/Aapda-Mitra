"""Small SQLite persistence layer for the hackathon dispatcher queue."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _connection(database_path: str) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: str) -> None:
    """Create the local report queue if it does not already exist."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    with _connection(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS rescue_reports (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                transcript TEXT NOT NULL,
                location TEXT,
                disaster_type TEXT NOT NULL,
                urgency_score INTEGER NOT NULL CHECK(urgency_score BETWEEN 0 AND 10),
                summary TEXT NOT NULL,
                recommended_action TEXT NOT NULL,
                caller_guidance TEXT NOT NULL,
                source_status TEXT NOT NULL,
                dispatcher_status TEXT NOT NULL
            )
            """
        )


def create_report(database_path: str, report: dict[str, str | int | None]) -> dict[str, str | int | None]:
    """Persist and return a newly created report."""
    columns = ", ".join(report)
    placeholders = ", ".join(f":{column}" for column in report)
    with _connection(database_path) as connection:
        connection.execute(
            f"INSERT INTO rescue_reports ({columns}) VALUES ({placeholders})", report
        )
    return report


def list_reports(database_path: str) -> list[dict[str, str | int | None]]:
    """Return highest-urgency and newest reports first."""
    with _connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT * FROM rescue_reports
            ORDER BY urgency_score DESC, created_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def approve_report(database_path: str, report_id: str) -> dict[str, str | int | None] | None:
    """Record the required human approval for a report."""
    with _connection(database_path) as connection:
        cursor = connection.execute(
            """
            UPDATE rescue_reports
            SET dispatcher_status = 'approved_by_human'
            WHERE id = ?
            """,
            (report_id,),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT * FROM rescue_reports WHERE id = ?", (report_id,)
        ).fetchone()
    return dict(row) if row else None
