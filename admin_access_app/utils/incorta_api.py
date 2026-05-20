import requests
import streamlit as st


def _base_url() -> str:
    return st.secrets["cluster"].rstrip("/")


def _tenant() -> str:
    return st.secrets["tenant"]


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {st.secrets['api_token']}",
        "Accept": "application/json",
    }


@st.cache_resource(show_spinner=False)
def _login_session() -> requests.Session:
    """Authenticate against Incorta and return a requests.Session.

    Uses the same credentials as the PostgreSQL connection (defined in
    [connections.postgresql]). The session carries the JSESSIONID cookie and
    the X-XSRF-TOKEN header required by /service/* endpoints.
    """
    server = _base_url()
    pg = st.secrets["connections"]["postgresql"]
    session = requests.Session()

    r = session.post(
        f"{server}/incorta/authservice/login",
        data={"tenant": _tenant(), "pass": pg["password"], "user": pg["username"]},
        timeout=30,
    )
    print(r.content)
    r.raise_for_status()

    r = session.get(f"{server}/incorta/service/user/isLoggedIn", timeout=30)
    r.raise_for_status()
    csrf = session.cookies.get("XSRF-TOKEN")
    if not csrf:
        raise RuntimeError("Login succeeded but no XSRF-TOKEN was returned.")
    session.headers["X-XSRF-TOKEN"] = csrf
    return session


@st.cache_data(show_spinner=False, ttl=1000)
def search_catalog(
    keyword: str = "",
    type: str = "ALL",
    limit: int = 200,
    offset: int = 0,
) -> dict:
    url = f"{_base_url()}/incorta/api/v2/{_tenant()}/catalog/search"
    params = {
        "type": type,
        "keyword": keyword,
        "limit": limit,
        "offset": offset,
    }
    prepared = requests.Request("GET", url, params=params).prepare()
    print(f"[incorta_api] GET {prepared.url}")
    response = requests.get(url, headers=_headers(), params=params, timeout=30)
    response.raise_for_status()
    return response.json()


def get_dashboards(keyword: str = None, limit: int = 200, offset: int = 0) -> dict:
    res = search_catalog(keyword=keyword, type="DASHBOARD", limit=limit, offset=offset)
    return res


def _service_post(url: str, payload: dict) -> requests.Response:
    session = _login_session()
    response = session.post(url, data=payload, timeout=30)
    # 401 = expired token; retry once with a fresh login
    if response.status_code == 401:
        _login_session.clear()
        session = _login_session()
        response = session.post(url, data=payload, timeout=30)
    return response


def _raise_incorta_error(response: requests.Response) -> None:
    """Raise an exception with the Incorta error body, falling back to HTTP status."""
    try:
        body = response.json()
        msg = body.get("error") or body.get("message") or str(body)
    except Exception:
        msg = response.text or f"HTTP {response.status_code}"
    raise requests.HTTPError(
        f"HTTP {response.status_code}: {msg}", response=response
    )


def create_permission(
    destination_id: int,
    content_id: int,
    *,
    destination_type: int = 0,
    content_type: int = 4,
    code: int = 1,
) -> dict:
    """Grant a permission on an Incorta content item to a user/group.

    Sent as application/x-www-form-urlencoded, matching the in-app network call.
    destinationType=0 → user, contentType=4 → dashboard, code=1 → view.
    """
    url = f"{_base_url()}/incorta/service/permission/createPermission"
    payload = {
        "destinationId": destination_id,
        "destinationType": destination_type,
        "contentId": content_id,
        "contentType": content_type,
        "code": code,
    }
    response = _service_post(url, payload)
    if response.status_code not in (200, 201):
        _raise_incorta_error(response)
    return response.json() if response.text else {}


def revoke_permission(
    destination_id: int,
    content_id: int,
    *,
    destination_type: int = 0,
    content_type: int = 4,
) -> None:
    """Revoke a permission on an Incorta content item from a user/group.

    Uses updatePermission with code=0 (revoke). Accepts 200 or 204.
    """
    url = f"{_base_url()}/incorta/service/permission/updatePermission"
    payload = {
        "destinationId": destination_id,
        "destinationType": destination_type,
        "contentId": content_id,
        "contentType": content_type,
        "code": 0,
    }
    response = _service_post(url, payload)
    if response.status_code not in (200, 204):
        _raise_incorta_error(response)
