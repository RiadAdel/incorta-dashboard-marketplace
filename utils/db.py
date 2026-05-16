import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


_DATA_DIR = Path("data")
_PARQUET_PATH = _DATA_DIR / "access_requests.parquet"
_LOCK = threading.Lock()

_SCHEMA = pa.schema(
    [
        ("request_id", pa.string()),
        ("requester_email", pa.string()),
        ("dashboard_identifier", pa.string()),
        ("dashboard_name", pa.string()),
        ("dashboard_path", pa.string()),
        ("note", pa.string()),
        ("status", pa.string()),
        ("created_at", pa.timestamp("us", tz="UTC")),
        ("decided_at", pa.timestamp("us", tz="UTC")),
        ("decided_by", pa.string()),
        ("decision_note", pa.string()),
    ]
)


def _empty_table() -> pa.Table:
    return pa.table(
        {name: pa.array([], type=t) for name, t in zip(_SCHEMA.names, _SCHEMA.types)},
        schema=_SCHEMA,
    )


def ensure_schema() -> None:
    """Create the parquet file with the expected schema if it doesn't exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not _PARQUET_PATH.exists():
        pq.write_table(_empty_table(), _PARQUET_PATH)


def insert_access_request(*, email: str, picks: list[dict], note: str | None) -> str:
    """Persist one access request as N rows (one per dashboard).

    All rows share the same `request_id` so the approver can group them.
    Writes are serialized via a process-wide lock and committed atomically
    via temp-file rename.
    """
    request_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    clean_note = (note or "").strip() or None
    n = len(picks)
    new_rows = pa.table(
        {
            "request_id": [request_id] * n,
            "requester_email": [email] * n,
            "dashboard_identifier": [p.get("identifier") for p in picks],
            "dashboard_name": [p.get("name") for p in picks],
            "dashboard_path": [p.get("path") for p in picks],
            "note": [clean_note] * n,
            "status": ["PENDING"] * n,
            "created_at": [now] * n,
            "decided_at": [None] * n,
            "decided_by": [None] * n,
            "decision_note": [None] * n,
        },
        schema=_SCHEMA,
    )

    with _LOCK:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        if _PARQUET_PATH.exists():
            existing = pq.read_table(_PARQUET_PATH, schema=_SCHEMA)
            combined = pa.concat_tables([existing, new_rows])
        else:
            combined = new_rows
        _atomic_write(combined)

    return request_id


def update_request_status(
    request_id: str,
    status: str,
    *,
    decided_by: str | None = None,
    decision_note: str | None = None,
) -> None:
    """Update every row sharing `request_id` to the given status + decision metadata."""
    now = datetime.now(timezone.utc)
    with _LOCK:
        if not _PARQUET_PATH.exists():
            return
        rows = pq.read_table(_PARQUET_PATH, schema=_SCHEMA).to_pylist()
        for row in rows:
            if row["request_id"] == request_id:
                row["status"] = status
                row["decided_at"] = now
                row["decided_by"] = decided_by
                row["decision_note"] = decision_note
        _atomic_write(pa.Table.from_pylist(rows, schema=_SCHEMA))


def _atomic_write(table: pa.Table) -> None:
    tmp = _PARQUET_PATH.with_suffix(".parquet.tmp")
    pq.write_table(table, tmp)
    tmp.replace(_PARQUET_PATH)
