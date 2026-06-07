---
name: using-incorta-api
description: Using Incorta's REST APIs from Python. Use when authenticating with Incorta, managing schemas/dashboards/permissions, importing/exporting tenant content, or calling any /service/* or /api/v2/* endpoint.
---

# Using the Incorta API

The `incorta.py` file in this project is the official Incorta Python API client. It wraps two distinct API surfaces with different auth mechanisms.

## Two API surfaces

| Surface | Base path | Auth |
|---------|-----------|------|
| Service API | `/incorta/service/*` | Session cookie (`JSESSIONID`) + `X-XSRF-TOKEN` header |
| Catalog API v2 | `/incorta/api/v2/{tenant}/*` | `Authorization: Bearer <api_token>` header |
| CMC API | `/cmc/api/v1/*` | `Authorization: basic <base64>` header |

---

## Authentication

### Service API — session login

```python
from incorta import login

session = login(
    server="https://your-cluster.incorta.com/incorta",
    tenant="default",
    login="admin",
    password="secret",
)
# session is a JSON string carrying: server, id_cookie, id, csrf, verify
```

The login flow:
1. `POST /authservice/login` → gets `JSESSIONID` cookie
2. `GET /service/user/isLoggedIn` → gets `XSRF-TOKEN` cookie
3. All subsequent `/service/*` requests send both the cookie and `X-XSRF-TOKEN` header

Always pass `session` (the JSON string) to every subsequent call.

### Catalog API v2 — bearer token

Used directly via `requests` with the token from `st.secrets["api_token"]`:

```python
headers = {"Authorization": f"Bearer {api_token}", "Accept": "application/json"}
response = requests.get(
    f"{cluster}/incorta/api/v2/{tenant}/catalog/search",
    headers=headers,
    params={"type": "DASHBOARD", "keyword": "sales", "limit": 50, "offset": 0},
)
```

---

## Schema operations

```python
from incorta import login, load_schema, load_schema_incremental, list_schemas

session = login(server, tenant, user, password)

# Full load from source
load_schema(session, "MySchema")

# Incremental load
load_schema_incremental(session, "MySchema")

# Load a single table
load_schema(session, "MySchema", table="MyTable")

# Load from staging area
load_schema(session, "MySchema", staging=True)

# List all schema names
print(list_schemas(session))
```

---

## Export & import

Export and import use `/service/tenant/export` and `/service/tenant/import`. Exported content is a `.zip` file.

```python
from incorta import login, export_dashboards, export_schemas, import_dashboards

session = login(server, tenant, user, password)

# Export specific dashboards
export_dashboards(session, "output.zip", "Finance/Sales", "HR/Headcount")

# Export dashboards with bookmarks and scheduler jobs
export_dashboards_with_attachments(session, "output.zip", True, True, "Finance/Sales")

# Export schemas
export_schemas(session, "schemas.zip", "SalesSchema", "HRSchema")

# Import dashboards (overwrite=True replaces existing content)
import_dashboards(session, "output.zip", overwrite=True)

# Import everything in a package
import_tenant(session, "full_backup.zip", overwrite=False)
```

Import-only values: `"all"`, `"datasource"`, `"schema"`, `"catalog"`, `"alert"`, `"session-variables"`.

---

## Permissions

### Permission codes and entity types

| Permission | Code | Entity | Type code |
|-----------|------|--------|-----------|
| view | 1 | user | 0 |
| share | 3 | group | 1 |
| edit | 7 | folder | 3 |
| revoke | 0 | dashboard | 4 |
| | | schema | 5 |
| | | datasource/connector | 6 |
| | | datafile | 7 |

```python
from incorta import login, grant_user_access, grant_group_access, revoke_user_access

session = login(server, tenant, user, password)

# Grant a user view access to a dashboard
grant_user_access(session, "alice@company.com", "dashboard", "Finance/Sales", permission="view")

# Grant a group edit access to a schema
grant_group_access(session, "DataTeam", "schema", "SalesSchema", permission="edit")

# Revoke access
revoke_user_access(session, "alice@company.com", "dashboard", "Finance/Sales")
```

For numeric IDs (as used in `utils/incorta_api.py`), call `grant_access` directly:

```python
from incorta import grant_access, get_entity, get_code

grant_access(
    session,
    principle_id=user_id,       # numeric user ID from _incortametadata."user"
    principle_type=get_entity("user"),   # 0
    subject_id=dashboard_id,    # numeric dashboard ID from _incortametadata.dashboard
    subject_type=get_entity("dashboard"),  # 4
    permission="view",
)
```

---

## Catalog search (v2 API)

Used in `utils/incorta_api.py` via bearer token, not the session client:

```python
GET /incorta/api/v2/{tenant}/catalog/search
  ?type=DASHBOARD      # ALL, DASHBOARD, SCHEMA, etc.
  &keyword=sales
  &limit=9
  &offset=0
```

Response shape:
```json
{
  "resultCount": 42,
  "results": [
    {
      "identifier": "abc-123-guid",
      "name": "Sales Overview",
      "path": "tenant/Finance/Sales Overview"
    }
  ]
}
```

The `identifier` field is a GUID. Use `utils/dashboards.py:resolve_dashboard_id` to convert it to the numeric `id` required by the permission API.

---

## ID resolution (this project)

The catalog API returns GUIDs; the permission API requires numeric IDs. This project resolves them via the Incorta metadata PostgreSQL database:

```python
# utils/users.py
resolve_user_id("alice@company.com")
# → SELECT id FROM _incortametadata."user" WHERE email = :email

# utils/dashboards.py
resolve_dashboard_id("abc-123-guid")
# → SELECT id FROM _incortametadata.dashboard WHERE guid = :guid
```

---

## Session caching in Streamlit

In Streamlit, the login session should be cached with `@st.cache_resource` (process-lifetime) and cleared on 401:

```python
@st.cache_resource(show_spinner=False)
def _login_session() -> requests.Session:
    ...

# On 401:
_login_session.clear()
session = _login_session()
```

Catalog search results can be cached with `@st.cache_data(ttl=1000)`.

---

## Running API calls from the CLI

`incorta.py` is also a CLI script. Any function in the `methods` dict can be called directly:

```bash
python incorta.py login <server> <tenant> <user> <password>
python incorta.py export_dashboards <session_json> output.zip "Finance/Sales"
python incorta.py load_schema <session_json> MySchema
```
