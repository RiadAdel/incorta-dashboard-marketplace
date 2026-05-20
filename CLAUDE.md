# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the dashboard request app (user-facing)
streamlit run request_access_app.py

# Run the access management app (admin-facing)
streamlit run access_app.py

# Install dependencies (using the project venv)
source .venv/bin/activate
pip install -r requirements.txt
```

There are no tests or linting configurations in this project.

## Architecture

This is two independent Streamlit apps that together form a self-service dashboard access request portal for Incorta.

**Shared setup — `utils/page_setup.py`**
`apply_theme()` handles light/dark theme detection and toggle (via injected JS that writes to `localStorage`), logo rendering, and per-theme CSS injection targeting Streamlit's internal `data-testid` attributes and `st-key-*` class patterns. Both apps call it after `st.set_page_config`.

**Apps**
- `request_access_app.py` — User-facing. Search Incorta dashboards (paginated, 9 per page), select one or more, and submit an access request via a dialog. Uses `@st.fragment` to isolate the dashboard grid so selection state doesn't cause full reruns.
- `access_app.py` — Admin-facing. Reads the Parquet file directly, groups rows by `request_id`, and lets admins approve (calls the Incorta API), reject, or revoke access.

**Utils**
- `utils/db.py` — All persistence. Stores access requests in `data/access_requests.parquet`. One request = N rows (one per dashboard), all sharing the same `request_id` UUID. Writes are serialized with a `threading.Lock` and committed atomically via temp-file rename. No database is used for request storage.
- `utils/incorta_api.py` — Two API surfaces:
  - Catalog search (`/api/v2/{tenant}/catalog/search`) uses a Bearer token from secrets — stateless, `@st.cache_data(ttl=1000)`.
  - Permission creation (`/service/permission/createPermission`) requires a session login (JSESSIONID + XSRF-TOKEN cookie flow) — session is cached with `@st.cache_resource` and refreshed on 401.
- `utils/users.py` — Resolves requester email → numeric user ID via SQL on `_incortametadata."user"`.
- `utils/dashboards.py` — Resolves dashboard GUID (returned by catalog API) → numeric ID via SQL on `_incortametadata.dashboard`. The catalog API returns GUIDs but `createPermission` requires numeric IDs.

**Secrets (`.streamlit/secrets.toml`)**
```toml
api_token = "..."        # Bearer token for catalog API
cluster   = "https://…" # Base URL of the Incorta cluster
tenant    = "..."        # Incorta tenant name

[connections.postgresql]
dialect  = "postgresql"
host     = "..."
port     = "..."
database = "..."
username = "..."
password = "..."         # Also used as the password for session login
```

The PostgreSQL connection (via `st.connection("postgresql")`) targets the Incorta metadata database and is used only for ID resolution lookups, not for storing access requests.
