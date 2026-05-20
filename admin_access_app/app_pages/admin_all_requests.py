import pandas as pd
import streamlit as st

from utils.db import get_all_requests

_ALL_STATUSES = ["PENDING", "APPROVED", "REJECTED", "REVOKED"]
_PAGE_SIZE = 50

st.title("All Requests", anchor=False)

try:
    with st.spinner("Loading requests…"):
        rows = get_all_requests()
except Exception as e:
    st.error(
        "We couldn't load the requests right now. Please try again in a moment.",
        icon=":material/cloud_off:",
    )
    with st.expander("Technical details"):
        st.code(str(e), language="text")
    st.stop()

if not rows:
    st.info("No access requests yet.", icon=":material/inbox:")
    st.stop()

df = pd.DataFrame(rows)

if df.empty:
    st.info("No access requests yet.", icon=":material/inbox:")
    st.stop()

# ── Filters + download ─────────────────────────────────────────────────────
f1, f2, f3, f4 = st.columns([3, 3, 3, 2], vertical_alignment="bottom")

status_filter: list[str] = f1.multiselect(
    "Status",
    options=_ALL_STATUSES,
    default=None,
    placeholder="All statuses",
)

email_filter: str = f2.text_input(
    "Requester email",
    placeholder="Filter by email…",
)

dashboard_filter: str = f3.text_input(
    "Dashboard name",
    placeholder="Filter by name…",
)

# ── Apply filters ───────────────────────────────────────────────────────────
filtered = df.copy()

if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]

if email_filter.strip():
    filtered = filtered[
        filtered["requester_email"].str.contains(
            email_filter.strip(), case=False, na=False
        )
    ]

if dashboard_filter.strip():
    filtered = filtered[
        filtered["dashboard_name"].str.contains(
            dashboard_filter.strip(), case=False, na=False
        )
    ]

# ── Download ────────────────────────────────────────────────────────────────
display_cols = [
    "status",
    "requester_email",
    "dashboard_name",
    "dashboard_path",
    "note",
    "created_at",
    "decided_at",
    "decided_by",
    "decision_note",
]

n_requests = filtered["request_id"].nunique()
n_rows = len(filtered)

csv_bytes = filtered[display_cols].to_csv(index=False).encode()
f4.download_button(
    "Download CSV",
    data=csv_bytes,
    file_name="access_requests.csv",
    mime="text/csv",
    icon=":material/download:",
    type="primary",
    width="stretch",
    disabled=n_rows == 0,
)

# ── Summary ─────────────────────────────────────────────────────────────────
total_pages = max(1, (n_rows + _PAGE_SIZE - 1) // _PAGE_SIZE)

# Reset to page 1 when filters change
filter_key = (tuple(status_filter), email_filter, dashboard_filter)
if st.session_state.get("_all_req_filter_key") != filter_key:
    st.session_state["_all_req_page"] = 1
    st.session_state["_all_req_filter_key"] = filter_key

page = st.session_state.get("_all_req_page", 1)
page = min(page, total_pages)

summary_col, page_col = st.columns([3, 2], vertical_alignment="center")
summary_col.caption(
    f"{n_requests} request{'s' if n_requests != 1 else ''}"
    f" · {n_rows} row{'s' if n_rows != 1 else ''}"
    + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
)

if total_pages > 1:
    with page_col.container(horizontal=True, horizontal_alignment="right"):
        if st.button(
            "",
            icon=":material/chevron_left:",
            key="prev_page",
            disabled=page <= 1,
        ):
            st.session_state["_all_req_page"] = page - 1
            st.rerun()
        st.markdown(f":small[**{page}** / {total_pages}]")
        if st.button(
            "",
            icon=":material/chevron_right:",
            key="next_page",
            disabled=page >= total_pages,
        ):
            st.session_state["_all_req_page"] = page + 1
            st.rerun()

# ── Table ───────────────────────────────────────────────────────────────────
if n_rows == 0:
    st.info("No requests match the current filters.", icon=":material/filter_list:")
    st.stop()

start = (page - 1) * _PAGE_SIZE
page_df = filtered[display_cols].iloc[start : start + _PAGE_SIZE]

st.dataframe(
    page_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "status": st.column_config.SelectboxColumn(
            "Status",
            options=_ALL_STATUSES,
            width="small",
            disabled=True,
        ),
        "requester_email": st.column_config.TextColumn("Requester", width="medium"),
        "dashboard_name": st.column_config.TextColumn("Dashboard", width="medium"),
        "dashboard_path": st.column_config.TextColumn("Path", width="medium"),
        "note": st.column_config.TextColumn("Note", width="medium"),
        "created_at": st.column_config.DatetimeColumn(
            "Submitted", format="MMM D, YYYY · HH:mm", width="medium"
        ),
        "decided_at": st.column_config.DatetimeColumn(
            "Decided", format="MMM D, YYYY · HH:mm", width="medium"
        ),
        "decided_by": st.column_config.TextColumn("Decided By", width="medium"),
        "decision_note": st.column_config.TextColumn("Decision Note", width="medium"),
    },
)
