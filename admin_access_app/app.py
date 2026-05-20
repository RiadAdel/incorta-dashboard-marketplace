import streamlit as st

st.set_page_config(
    page_title="Access requests",
    page_icon="static/incorta-logo.svg",
    layout="wide",
)

from utils.db import ensure_schema
from utils.page_setup import apply_theme

try:
    ensure_schema()
except Exception as e:
    apply_theme()
    st.error(
        "We couldn't connect to the database. "
        "Please try refreshing the page, or contact support if the issue persists.",
        icon=":material/cloud_off:",
    )
    with st.expander("Technical details"):
        st.code(str(e), language="text")
    st.stop()

apply_theme()

pg = st.navigation(
    [
        st.Page(
            "app_pages/admin_review.py",
            title="Review Requests",
            icon=":material/rate_review:",
        ),
        st.Page(
            "app_pages/admin_all_requests.py",
            title="All Requests",
            icon=":material/table:",
        ),
    ],
    position="top",
)
pg.run()
