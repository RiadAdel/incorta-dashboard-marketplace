import streamlit as st
from collections import defaultdict
from datetime import datetime, timezone

from utils.db import get_requests_for_email

_PAGE_SIZE = 10

_STATUS_BADGE = {
    "PENDING":  ":orange-badge[:material/pending: Pending]",
    "APPROVED": ":green-badge[:material/check_circle: Approved]",
    "REJECTED": ":red-badge[:material/cancel: Rejected]",
    "REVOKED":  ":gray-badge[:material/block: Revoked]",
}


def _fmt_ts(ts) -> str:
    if ts is None:
        return "—"
    try:
        return ts.strftime("%b %d, %Y %H:%M UTC")
    except (ValueError, AttributeError):
        return "—"


def _short_path(path: str) -> str:
    parts = (path or "").split("/", 1)
    return parts[1] if len(parts) > 1 else (path or "")


st.title("My Requests", anchor=False)

email = st.text_input(
    "Your email",
    value=st.session_state.get("requester_email", ""),
    placeholder="Type 3+ characters of your email and press Enter…",
    label_visibility="collapsed",
)

needle = (email or "").strip()

if not needle:
    st.info("Enter your email above to see your access requests.", icon=":material/info:")
    st.stop()

if len(needle) < 3:
    st.info(
        "Type at least 3 characters to search your requests.",
        icon=":material/info:",
    )
    st.stop()

try:
    with st.spinner("Loading your requests…"):
        rows = get_requests_for_email(needle)
except Exception as e:
    st.error(
        "We couldn't load your requests right now. Please try again in a moment.",
        icon=":material/cloud_off:",
    )
    with st.expander("Technical details"):
        st.code(str(e), language="text")
    st.stop()

if not rows:
    st.info(
        f"No access requests found matching “{needle}”.",
        icon=":material/inbox:",
    )
    st.stop()

groups: dict[str, list] = defaultdict(list)
for row in rows:
    groups[row["request_id"]].append(row)

sorted_groups = sorted(
    groups.items(),
    key=lambda kv: kv[1][0]["created_at"] or datetime.min.replace(tzinfo=timezone.utc),
    reverse=True,
)

n = len(sorted_groups)
total_pages = max(1, (n + _PAGE_SIZE - 1) // _PAGE_SIZE)

if st.session_state.get("_my_req_email") != needle:
    st.session_state["_my_req_page"] = 1
    st.session_state["_my_req_email"] = needle

page = min(st.session_state.get("_my_req_page", 1), total_pages)

summary_col, page_col = st.columns([3, 2], vertical_alignment="center")
summary_col.caption(
    f"{n} request{'s' if n != 1 else ''}"
    + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
)

if total_pages > 1:
    with page_col.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "",
            icon=":material/chevron_left:",
            key="prev_page",
            disabled=page <= 1,
            help="Previous page",
        ):
            st.session_state["_my_req_page"] = page - 1
            st.rerun()
        st.markdown(f":small[**{page}** / {total_pages}]")
        if st.button(
            "",
            icon=":material/chevron_right:",
            key="next_page",
            disabled=page >= total_pages,
            help="Next page",
        ):
            st.session_state["_my_req_page"] = page + 1
            st.rerun()

start = (page - 1) * _PAGE_SIZE
page_groups = sorted_groups[start : start + _PAGE_SIZE]

for req_id, req_rows in page_groups:
    first = req_rows[0]
    status = first.get("status", "PENDING")

    with st.container(border=True, key=f"req_card_{req_id}"):

        # ── Header: status badge + submission date ─────────────────
        col_status, col_date = st.columns([3, 2], vertical_alignment="center")
        with col_status:
            st.markdown(_STATUS_BADGE.get(status, status))
        with col_date.container(horizontal_alignment="right"):
            st.caption(f"Submitted {_fmt_ts(first.get('created_at'))}")

        st.divider()

        # ── Dashboard list ─────────────────────────────────────────
        n_dash = len(req_rows)
        st.caption(f"{n_dash} dashboard{'s' if n_dash != 1 else ''}")
        for r in req_rows:
            st.markdown(
                f":material/space_dashboard: **{r['dashboard_name']}**"
                f" &nbsp; :small[{_short_path(r.get('dashboard_path', ''))}]"
            )

        # ── Your note & decision meta ──────────────────────────────
        if first.get("note"):
            with st.expander(":material/notes: Your note"):
                st.write(first["note"])

        if first.get("decided_at") or first.get("decided_by") or first.get("decision_note"):
            decided_by = first.get("decided_by") or "—"
            with st.expander(
                f":material/gavel: Decision · {decided_by} · {_fmt_ts(first.get('decided_at'))}"
            ):
                st.write(first.get("decision_note") or "_No note provided._")
