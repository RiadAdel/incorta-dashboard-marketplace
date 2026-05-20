import streamlit as st
import streamlit.components.v1 as components

from collections import OrderedDict

from utils.db import get_all_requests, update_request_status
from utils.dashboards import resolve_dashboard_id
from utils.incorta_api import create_permission, revoke_permission
from utils.users import resolve_user_id

_PAGE_SIZE = 10

_STATUS_BADGE = {
    "PENDING": ":orange-badge[Pending]",
    "APPROVED": ":green-badge[Approved]",
    "REJECTED": ":red-badge[Rejected]",
    "REVOKED": ":gray-badge[Revoked]",
}


def _short_path(path: str) -> str:
    parts = (path or "").split("/", 1)
    return parts[1] if len(parts) > 1 else (path or "")


def _fmt_ts(ts) -> str:
    if ts is None:
        return "—"
    try:
        return ts.strftime("%b %d, %Y · %H:%M UTC")
    except (ValueError, AttributeError):
        return "—"


def _approve_request(request_id: str, email: str, items: list[dict]) -> None:
    with st.spinner("Granting access…"):
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

    try:
        update_request_status(request_id, "APPROVED")
    except Exception as e:
        st.error(
            "Access was granted in Incorta but the status couldn't be saved. Please refresh the page.",
            icon=":material/warning:",
        )
        with st.expander("Technical details"):
            st.code(str(e), language="text")
        return
    st.rerun()


def _revoke_request(request_id: str, email: str, items: list[dict]) -> None:
    with st.spinner("Revoking access…"):
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
                revoke_permission(destination_id=user_id, content_id=content_id)
        except Exception as e:
            st.error("Couldn't revoke access in Incorta. No status change applied.")
            with st.expander("Technical details"):
                st.code(str(e), language="text")
            return

    try:
        update_request_status(request_id, "REVOKED")
    except Exception as e:
        st.error(
            "Access was revoked in Incorta but the status couldn't be saved. Please refresh the page.",
            icon=":material/warning:",
        )
        with st.expander("Technical details"):
            st.code(str(e), language="text")
        return
    st.rerun()


st.title("Access requests", anchor=False)

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

keyword = st.text_input(
    "Search requests",
    placeholder="Type 3+ characters to filter…",
    key="admin_search",
    label_visibility="collapsed",
)

components.html("""
<script>
(function () {
    const LS_KEY = 'incorta_admin_search_refocus';

    function getInput() {
        return window.parent.document.querySelector('.st-key-admin_search input');
    }

    function tryRefocus() {
        if (window.parent.localStorage.getItem(LS_KEY) !== '1') return;
        const inp = getInput();
        if (!inp) return;
        window.parent.localStorage.removeItem(LS_KEY);
        inp.focus();
    }

    function attach(inp) {
        if (inp._lsAttached) return;
        inp._lsAttached = true;
        let timer;
        inp.addEventListener('input', function () {
            clearTimeout(timer);
            const len = this.value.trim().length;
            if (len >= 3 || len === 0) {
                timer = setTimeout(() => {
                    window.parent.localStorage.setItem(LS_KEY, '1');
                    inp.dispatchEvent(new FocusEvent('focusout', { bubbles: true }));
                }, 400);
            }
        });
    }

    function init() {
        const inp = getInput();
        if (inp) attach(inp);
        tryRefocus();
    }

    new MutationObserver(init).observe(window.parent.document.body, {
        childList: true,
        subtree: true,
    });
    setTimeout(init, 150);
})();
</script>
""", height=0)

statuses = ["All"] + sorted({r["status"] for r in rows})
status_filter = st.segmented_control(
    "Status",
    statuses,
    default="PENDING" if "PENDING" in statuses else "All",
    label_visibility="collapsed",
)

if status_filter and status_filter != "All":
    rows = [r for r in rows if r["status"] == status_filter]

if keyword and len(keyword.strip()) >= 3:
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

n_groups = len(groups)
total_pages = max(1, (n_groups + _PAGE_SIZE - 1) // _PAGE_SIZE)

filter_key = (status_filter, keyword)
if st.session_state.get("_review_filter_key") != filter_key:
    st.session_state["_review_page"] = 1
    st.session_state["_review_filter_key"] = filter_key

page = min(st.session_state.get("_review_page", 1), total_pages)

summary_col, page_col = st.columns([3, 2], vertical_alignment="center")
summary_col.caption(
    f"{n_groups} request{'s' if n_groups != 1 else ''}"
    f" · {len(rows)} dashboard{'s' if len(rows) != 1 else ''}"
    + (f" · page {page} of {total_pages}" if total_pages > 1 else "")
)

if total_pages > 1:
    with page_col.container(horizontal=True, horizontal_alignment="right"):
        if st.button("", icon=":material/chevron_left:", key="prev_page", disabled=page <= 1):
            st.session_state["_review_page"] = page - 1
            st.rerun()
        st.markdown(f":small[**{page}** / {total_pages}]")
        if st.button("", icon=":material/chevron_right:", key="next_page", disabled=page >= total_pages):
            st.session_state["_review_page"] = page + 1
            st.rerun()

start = (page - 1) * _PAGE_SIZE
page_groups = list(groups.items())[start : start + _PAGE_SIZE]

for request_id, items in page_groups:
    head = items[0]
    with st.container(border=True, key=f"req_card_{request_id}"):

        # ── Header: requester identity + status badge ──────────────
        col_info, col_badge = st.columns([5, 1], vertical_alignment="center")
        with col_info:
            st.markdown(f":material/person: &nbsp;**{head['requester_email']}**")
            st.caption(f"Submitted {_fmt_ts(head['created_at'])}")
        with col_badge.container(horizontal_alignment="right"):
            st.markdown(_STATUS_BADGE.get(head["status"], head["status"]))

        st.divider()

        # ── Dashboard list ─────────────────────────────────────────
        n = len(items)
        st.caption(f"{n} dashboard{'s' if n != 1 else ''} requested")
        for it in items:
            st.markdown(
                f":material/dashboard: **{it['dashboard_name'] or it['dashboard_identifier']}**"
                f" &nbsp; :small[{_short_path(it['dashboard_path'] or '')}]"
            )

        # ── Note & decision meta ───────────────────────────────────
        if head["note"]:
            with st.expander(":material/notes: Requester note"):
                st.write(head["note"])

        if head["decided_at"] or head["decided_by"] or head["decision_note"]:
            decided_by = head["decided_by"] or "—"
            with st.expander(
                f":material/gavel: Decision · {decided_by} · {_fmt_ts(head['decided_at'])}"
            ):
                st.write(head["decision_note"] or "_No note provided._")

        # ── Actions ────────────────────────────────────────────────
        if head["status"] == "PENDING":
            st.divider()
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
                try:
                    with st.spinner("Rejecting request…"):
                        update_request_status(request_id, "REJECTED")
                except Exception as e:
                    st.error(
                        "Couldn't update the request status. Please try again.",
                        icon=":material/error:",
                    )
                    with st.expander("Technical details"):
                        st.code(str(e), language="text")
                else:
                    st.rerun()
        elif head["status"] == "APPROVED":
            st.divider()
            if st.button(
                "Revoke access",
                key=f"revoke_{request_id}",
                icon=":material/person_remove:",
                width="stretch",
            ):
                _revoke_request(request_id, head["requester_email"], items)
