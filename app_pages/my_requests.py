import streamlit as st
from collections import defaultdict
from datetime import datetime, timezone

from utils.db import get_requests_for_email

_STATUS_ICON = {
    "APPROVED": ":material/check_circle:",
    "REJECTED": ":material/cancel:",
    "PENDING": ":material/pending:",
}
_STATUS_COLOR = {
    "APPROVED": "green",
    "REJECTED": "red",
    "PENDING": "orange",
}


def _fmt_ts(ts) -> str:
    if not ts:
        return "—"
    return ts.strftime("%b %d, %Y %H:%M UTC")


def _short_path(path: str) -> str:
    parts = (path or "").split("/", 1)
    return parts[1] if len(parts) > 1 else (path or "")


st.title("My Requests", anchor=False)

email = st.text_input(
    "Your email",
    value=st.session_state.get("requester_email", ""),
    placeholder="you@company.com",
    label_visibility="collapsed",
)

if not email or not email.strip():
    st.info("Enter your email above to see your access requests.", icon=":material/info:")
    st.stop()

rows = get_requests_for_email(email.strip())

if not rows:
    st.info("No access requests found for this email.", icon=":material/inbox:")
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
st.caption(f"{n} request{'s' if n != 1 else ''}")

for req_id, req_rows in sorted_groups:
    first = req_rows[0]
    status = first.get("status", "PENDING")
    color = _STATUS_COLOR.get(status, "orange")
    icon = _STATUS_ICON.get(status, ":material/pending:")

    with st.container(border=True, key=f"req_card_{req_id}"):
        header_left, header_right = st.columns([3, 2], vertical_alignment="center")
        with header_left:
            st.markdown(f":{color}[{icon} **{status}**]")
        header_right.caption(f"Submitted {_fmt_ts(first.get('created_at'))}")

        st.markdown(
            "\n".join(
                f"- :material/dashboard: **{r['dashboard_name']}**"
                f"  :small[{_short_path(r.get('dashboard_path', ''))}]"
                for r in req_rows
            )
        )

        if first.get("note"):
            st.markdown(f":small[**Note:** {first['note']}]")

        if first.get("decision_note"):
            st.markdown(f":small[**Decision note:** {first['decision_note']}]")

        if first.get("decided_by"):
            st.caption(
                f"Decided by {first['decided_by']} · {_fmt_ts(first.get('decided_at'))}"
            )
