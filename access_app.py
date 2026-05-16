from collections import OrderedDict
from pathlib import Path

import streamlit as st

from utils.db import ensure_schema, update_request_status
from utils.dashboards import resolve_dashboard_id
from utils.incorta_api import create_permission
from utils.users import resolve_user_id

import pyarrow.parquet as pq

_PARQUET_PATH = Path("data/access_requests.parquet")

_STATUS_BADGE = {
    "PENDING": ":orange-badge[Pending]",
    "APPROVED": ":green-badge[Approved]",
    "REJECTED": ":red-badge[Rejected]",
}


def _short_path(path: str) -> str:
    parts = (path or "").split("/", 1)
    return parts[1] if len(parts) > 1 else (path or "")


def _fmt_ts(ts) -> str:
    if ts is None:
        return "—"
    return ts.strftime("%b %d, %Y · %H:%M UTC")


def _approve_request(request_id: str, email: str, items: list[dict]) -> None:
    print(items)
    try:
        user_id = resolve_user_id(email)
    except Exception as e:
        st.error(f"Couldn't look up user `{email}`.")
        with st.expander("Technical details"):
            st.code(str(e), language="text")
        return

    if user_id is None:
        st.error(f"No Incorta user found for `{email}`.")
        return

    try:
        for it in items:
            content_id = resolve_dashboard_id(it["dashboard_identifier"])
            if content_id is None:
                st.error(
                    f"Couldn't resolve dashboard "
                    f"`{it['dashboard_name'] or it['dashboard_identifier']}`."
                )
                return
            create_permission(destination_id=user_id, content_id=content_id)
    except Exception as e:
        st.error("Couldn't grant access in Incorta. No status change applied.")
        with st.expander("Technical details"):
            st.code(str(e), language="text")
        return

    update_request_status(request_id, "APPROVED")
    st.rerun()


ensure_schema()

st.title("Access requests", anchor=False)

table = pq.read_table(_PARQUET_PATH)
rows = table.to_pylist()

if not rows:
    st.info("No access requests yet.", icon=":material/inbox:")
    st.stop()

_search_options = sorted(
    {r["requester_email"] for r in rows if r.get("requester_email")}
    | {r["dashboard_name"] for r in rows if r.get("dashboard_name")}
)
keyword = st.selectbox(
    "Search requests",
    options=_search_options,
    index=None,
    placeholder="Search by email or dashboard name…",
    label_visibility="collapsed",
)

statuses = ["All"] + sorted({r["status"] for r in rows})
status_filter = st.segmented_control(
    "Status",
    statuses,
    default="PENDING" if "PENDING" in statuses else "All",
    label_visibility="collapsed",
)

if status_filter and status_filter != "All":
    rows = [r for r in rows if r["status"] == status_filter]

if keyword:
    needle = keyword.strip().lower()
    matching_request_ids = {
        r["request_id"]
        for r in rows
        if needle in (r.get("requester_email") or "").lower()
        or needle in (r.get("dashboard_name") or "").lower()
    }
    rows = [r for r in rows if r["request_id"] in matching_request_ids]

groups: OrderedDict[str, list[dict]] = OrderedDict()
for r in sorted(rows, key=lambda r: r["created_at"], reverse=True):
    groups.setdefault(r["request_id"], []).append(r)

st.caption(
    f"{len(groups)} request{'s' if len(groups) != 1 else ''}"
    f" · {len(rows)} dashboard{'s' if len(rows) != 1 else ''}"
)

for request_id, items in groups.items():
    head = items[0]
    with st.container(border=True, key=f"req_card_{request_id}"):
        top_left, top_right = st.columns([3, 1], vertical_alignment="center")
        with top_left:
            st.markdown(f"**{head['requester_email']}**")
            st.caption(_fmt_ts(head["created_at"]))
        with top_right.container(horizontal_alignment="right"):
            st.markdown(_STATUS_BADGE.get(head["status"], head["status"]))

        for it in items:
            st.markdown(
                f"- :material/dashboard: **{it['dashboard_name'] or it['dashboard_identifier']}**"
                f" &nbsp; :small[{_short_path(it['dashboard_path'] or '')}]"
            )

        if head["note"]:
            with st.expander("Requester note"):
                st.write(head["note"])

        if head["decided_at"] or head["decided_by"] or head["decision_note"]:
            decided_by = head["decided_by"] or "—"
            with st.expander(
                f"Decision by {decided_by} on {_fmt_ts(head['decided_at'])}"
            ):
                st.write(head["decision_note"] or "_No note provided._")

        if head["status"] == "PENDING":
            c1, c2 = st.columns(2)
            if c1.button(
                "Approve",
                key=f"approve_{request_id}",
                type="primary",
                icon=":material/check:",
                width="stretch",
            ):
                _approve_request(request_id, head["requester_email"], items)
            if c2.button(
                "Reject",
                key=f"reject_{request_id}",
                icon=":material/close:",
                width="stretch",
            ):
                update_request_status(request_id, "REJECTED")
                st.rerun()
