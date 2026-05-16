from datetime import datetime, timezone

import re

import requests
import streamlit as st

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

from utils.db import ensure_schema, insert_access_request
from utils.incorta_api import get_dashboards

PAGE_SIZE = 9


def _fmt_date(ms: int | None) -> str:
    if not ms:
        return "—"
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%b %d, %Y")


def _short_path(path: str) -> str:
    parts = (path or "").split("/", 1)
    return parts[1] if len(parts) > 1 else (path or "")


ensure_schema()

st.title("Request dashboard access", anchor=False)

keyword = st.text_input(
    "Search dashboards",
    placeholder="Type a keyword and press Enter…",
    label_visibility="collapsed",
)

if st.session_state.get("_last_keyword") != keyword:
    st.session_state.page = 0
    st.session_state["_last_keyword"] = keyword
page = st.session_state.setdefault("page", 0)

try:
    result = get_dashboards(keyword=keyword, limit=PAGE_SIZE, offset=page * PAGE_SIZE)
except requests.HTTPError as e:
    st.error(
        f"Couldn't load dashboards (HTTP {e.response.status_code}). "
        "Please try again in a moment, or contact support if the problem continues."
    )
    with st.expander("Technical details"):
        st.code(e.response.text or str(e), language="text")
    st.stop()
except requests.RequestException as e:
    st.error(
        "We couldn't reach Incorta to load dashboards. "
        "Please check your connection and try again."
    )
    with st.expander("Technical details"):
        st.code(str(e), language="text")
    st.stop()

items = result.get("results", []) if isinstance(result, dict) else []
total = (
    result.get("resultCount", len(items)) if isinstance(result, dict) else len(items)
)

if "selected_dashboards" not in st.session_state:
    st.session_state.selected_dashboards = {}
selected = st.session_state.selected_dashboards


def _toggle(item: dict):
    ident = item["identifier"]
    if st.session_state.get(f"select_{ident}"):
        selected[ident] = item
    else:
        selected.pop(ident, None)


@st.dialog("Request access", dismissible=True)
def _request_access_dialog(picks: list[dict]):
    st.write(
        f"You're requesting access to **{len(picks)}** dashboard{'s' if len(picks) != 1 else ''}:"
    )
    for p in picks:
        st.markdown(
            f"- :material/dashboard: **{p.get('name')}** &nbsp; :small[{_short_path(p.get('path', ''))}]"
        )
    email = st.text_input(
        "Your email",
        value=st.session_state.get("requester_email", ""),
        placeholder="you@company.com",
        help="We'll grant access to this email address.",
    )
    note = st.text_area(
        "Optional note for the approver", placeholder="Why do you need access?"
    )

    email_valid = bool(_EMAIL_RE.match(email.strip()))
    if email and not email_valid:
        st.warning("Please enter a valid email address.", icon=":material/warning:")

    cols = st.columns(2)
    if cols[0].button("Cancel", width="stretch"):
        st.rerun()
    if cols[1].button(
        "Submit request",
        type="primary",
        width="stretch",
        disabled=not email_valid,
    ):
        try:
            request_id = insert_access_request(
                email=email.strip(), picks=picks, note=note
            )
        except Exception as e:
            st.error(
                "We couldn't save your request. Please try again, or contact "
                "support if the problem continues."
            )
            with st.expander("Technical details"):
                st.code(str(e), language="text")
            return
        st.session_state["requester_email"] = email.strip()
        st.session_state["_last_request"] = {
            "items": picks,
            "note": note,
            "email": email.strip(),
            "request_id": request_id,
        }
        st.session_state.selected_dashboards = {}
        st.rerun()


if msg := st.session_state.pop("_last_request", None):
    st.success(
        f"Access request submitted for {len(msg['items'])} dashboard"
        f"{'s' if len(msg['items']) != 1 else ''}. An approver will review it shortly.",
        icon=":material/check_circle:",
    )

total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
page = min(page, total_pages - 1)
st.session_state.page = page


@st.fragment
def render_dashboards():
    selected = st.session_state.selected_dashboards

    with st.container(border=True, key="dash_action_bar"):
        left, right = st.columns([3, 2], vertical_alignment="center")
        with left:
            if selected:
                st.markdown(f"**{len(selected)}** selected")
            else:
                st.markdown(":small[Select dashboards to request access]")
        with right.container(horizontal=True, horizontal_alignment="right"):
            st.button(
                "Clear",
                disabled=not selected,
                on_click=lambda: st.session_state.selected_dashboards.clear(),
            )
            if st.button(
                "Request access",
                type="primary",
                icon=":material/lock_open:",
                disabled=not selected,
            ):
                _request_access_dialog(list(selected.values()))

    st.caption(
        f"{total} dashboard{'s' if total != 1 else ''} found"
        f"{f' · page {page + 1} of {total_pages}' if total_pages > 1 else ''}"
    )

    if not items:
        st.info("No dashboards match your search.", icon=":material/info:")
        return

    cols_per_row = 3
    for row_start in range(0, len(items), cols_per_row):
        row = items[row_start : row_start + cols_per_row]
        cols = st.columns(cols_per_row, gap="medium")
        for col, item in zip(cols, row):
            ident = item["identifier"]
            with col.container(border=True, height="stretch", key=f"dash_card_{ident}"):
                st.checkbox(
                    f"**{item.get('name', 'Untitled')}**",
                    key=f"select_{ident}",
                    value=ident in selected,
                    on_change=_toggle,
                    args=(item,),
                )
                st.caption(_short_path(item.get("path", "")))
                st.markdown(
                    f":small[**Created**] {_fmt_date(item.get('creationDate'))}"
                )

    if total_pages > 1:
        st.space("small")
        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.button(
                "Previous", icon=":material/chevron_left:", disabled=page == 0
            ):
                st.session_state.page = page - 1
                st.rerun(scope="app")
            st.markdown(f":small[Page **{page + 1}** of **{total_pages}**]")
            if st.button(
                "Next",
                icon=":material/chevron_right:",
                disabled=page >= total_pages - 1,
            ):
                st.session_state.page = page + 1
                st.rerun(scope="app")


render_dashboards()
