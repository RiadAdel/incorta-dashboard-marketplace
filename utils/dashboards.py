import streamlit as st


@st.cache_data(ttl=300, show_spinner=False)
def resolve_dashboard_id(guid: str) -> int | None:
    """Look up a dashboard's numeric ID by GUID from _incortametadata.dashboard.

    The catalog API returns a GUID as `identifier`, but createPermission expects
    the numeric `id`. Returns None if no row matches. Cached for 5 minutes.
    """
    if not guid:
        return None
    conn = st.connection("postgresql", type="sql")
    df = conn.query(
        "SELECT id FROM _incortametadata.dashboard WHERE guid = :guid LIMIT 1",
        params={"guid": guid},
        ttl=0,
    )
    if df.empty:
        return None
    return int(df.iloc[0]["id"])
