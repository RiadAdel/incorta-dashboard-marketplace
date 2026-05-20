import streamlit as st

st.set_page_config(
    page_title="Access requests",
    page_icon="static/incorta-logo.svg",
    layout="wide",
)

from utils.db import ensure_schema
from utils.page_setup import apply_theme

ensure_schema()
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
