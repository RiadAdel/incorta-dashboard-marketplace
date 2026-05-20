import uuid
from datetime import datetime, timezone

import streamlit as st
from sqlalchemy import text


def _conn():
    return st.connection("marketplace", type="sql")


def ensure_schema() -> None:
    with _conn().session as s:
        s.execute(text("""
            CREATE TABLE IF NOT EXISTS access_requests (
                request_id           TEXT        NOT NULL,
                requester_email      TEXT        NOT NULL,
                dashboard_identifier TEXT,
                dashboard_name       TEXT,
                dashboard_path       TEXT,
                note                 TEXT,
                status               TEXT        NOT NULL DEFAULT 'PENDING',
                created_at           TIMESTAMPTZ NOT NULL,
                decided_at           TIMESTAMPTZ,
                decided_by           TEXT,
                decision_note        TEXT
            )
        """))
        s.commit()


def insert_access_request(*, email: str, picks: list[dict], note: str | None) -> str:
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    clean_note = (note or "").strip() or None

    with _conn().session as s:
        for p in picks:
            s.execute(
                text("""
                    INSERT INTO access_requests
                        (request_id, requester_email, dashboard_identifier,
                         dashboard_name, dashboard_path, note, status, created_at,
                         decided_at, decided_by, decision_note)
                    VALUES
                        (:request_id, :requester_email, :dashboard_identifier,
                         :dashboard_name, :dashboard_path, :note, 'PENDING', :created_at,
                         NULL, NULL, NULL)
                """),
                {
                    "request_id": request_id,
                    "requester_email": email,
                    "dashboard_identifier": p.get("identifier"),
                    "dashboard_name": p.get("name"),
                    "dashboard_path": p.get("path"),
                    "note": clean_note,
                    "created_at": now,
                },
            )
        s.commit()

    return request_id


def update_request_status(
    request_id: str,
    status: str,
    *,
    decided_by: str | None = None,
    decision_note: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    with _conn().session as s:
        s.execute(
            text("""
                UPDATE access_requests
                SET status        = :status,
                    decided_at    = :decided_at,
                    decided_by    = :decided_by,
                    decision_note = :decision_note
                WHERE request_id = :request_id
            """),
            {
                "status": status,
                "decided_at": now,
                "decided_by": decided_by,
                "decision_note": decision_note,
                "request_id": request_id,
            },
        )
        s.commit()


def get_requests_for_email(email: str) -> list[dict]:
    df = _conn().query(
        "SELECT * FROM access_requests WHERE requester_email = :email ORDER BY created_at DESC",
        params={"email": email},
        ttl=0,
    )
    return df.to_dict(orient="records")


def get_all_requests() -> list[dict]:
    df = _conn().query(
        "SELECT * FROM access_requests ORDER BY created_at DESC",
        ttl=0,
    )
    return df.to_dict(orient="records")
