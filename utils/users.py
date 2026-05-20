import streamlit as st
from sqlalchemy import text


@st.cache_data(ttl=300, show_spinner=False)
def resolve_user_id(email: str) -> int | None:
    """Look up an Incorta user ID by email from _incortametadata.user.

    Returns None if no row matches. Cached for 5 minutes per email.
    """
    if not email:
        return None
    conn = st.connection("postgresql", type="sql")
    df = conn.query(
        'SELECT id FROM _incortametadata."user" WHERE email = :email LIMIT 1',
        params={"email": email},
        ttl=0,
    )

    print(df.iloc[0]["id"])
    if df.empty:
        return None
    return int(df.iloc[0]["id"])
