import streamlit as st

st.set_page_config(
    page_title="Incorta dashboards",
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
            "app_pages/browse.py",
            title="Browse Dashboards",
            icon=":material/search:",
        ),
        st.Page(
            "app_pages/my_requests.py",
            title="My Requests",
            icon=":material/inbox:",
        ),
    ],
    position="top",
)
pg.run()
