import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Incorta dashboards",
    page_icon="static/incorta-logo.svg",
    layout="wide",
)

_current_theme = getattr(getattr(st.context, "theme", None), "type", "dark") or "dark"

_logo_path = (
    "static/incorta-logo-dark.svg"
    if _current_theme == "light"
    else "static/incorta-logo.svg"
)

_, logo_col, toggle_col = st.columns([1, 4, 1], vertical_alignment="center")
with logo_col.container(horizontal_alignment="center"):
    st.image(_logo_path, width=280)
with toggle_col.container(horizontal=True, horizontal_alignment="right"):
    if _current_theme == "dark":
        _label, _tooltip = "🌞", "Switch to light mode"
    else:
        _label, _tooltip = "🌙", "Switch to dark mode"
    if st.button(_label, key="theme_toggle", help=_tooltip):
        _new_theme = "light" if _current_theme == "dark" else "dark"
        _js_value = "Dark" if _new_theme == "dark" else "Light"
        components.html(
            f"""
            <script>
                const value = JSON.stringify("{_js_value}");
                const ls = window.parent.localStorage;
                ['/', '/request', '/access', window.parent.location.pathname]
                    .forEach(p => ls.setItem(`stActiveTheme-${{p}}-v2`, value));
                Object.keys(ls)
                    .filter(k => k.startsWith('stActiveTheme-') && k.endsWith('-v2'))
                    .forEach(k => ls.setItem(k, value));
                window.parent.location.reload();
            </script>
            """,
            height=0,
        )
        st.stop()

if _current_theme == "dark":
    _bg_gradient = (
        "radial-gradient(ellipse at top left, #2a1554 0%, transparent 55%),"
        "radial-gradient(ellipse at bottom right, #4c1d95 0%, transparent 55%),"
        "linear-gradient(135deg, #0d0a2e 0%, #1a1350 100%)"
    )
    _title_gradient = "linear-gradient(135deg, #c4b5fd 0%, #f0abfc 50%, #fb7185 100%)"
    _card_bg = "rgba(255, 255, 255, 0.06)"
    _card_border = "rgba(255, 255, 255, 0.12)"
    _card_shadow = "0 8px 32px rgba(0, 0, 0, 0.32)"
    _caption_color = "#c4bce0"
    _body_color = "#f1eff7"
else:
    _bg_gradient = (
        "radial-gradient(ellipse at top left, #ede7f9 0%, transparent 55%),"
        "radial-gradient(ellipse at bottom right, #fce7f3 0%, transparent 55%),"
        "linear-gradient(135deg, #ffffff 0%, #f4f1fb 100%)"
    )
    _title_gradient = "linear-gradient(135deg, #7c3aed 0%, #db2777 100%)"
    _card_bg = "rgba(255, 255, 255, 0.55)"
    _card_border = "rgba(124, 58, 237, 0.18)"
    _card_shadow = "0 8px 32px rgba(124, 58, 237, 0.08)"
    _caption_color = "#4a4458"
    _body_color = "#15152b"

st.markdown(
    f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background: {_bg_gradient} fixed;
    }}
    [data-testid="stHeader"] {{
        background: transparent;
    }}
    [data-testid="stHeading"] h1,
    [data-testid="stHeading"] h2 {{
        background: {_title_gradient};
        -webkit-background-clip: text;
        background-clip: text;
        -webkit-text-fill-color: transparent;
        color: transparent;
    }}
    [data-testid="stBaseButton-primary"] {{
        background: linear-gradient(135deg, #7c3aed 0%, #db2777 100%) !important;
        border: none !important;
        color: #ffffff !important;
        transition: filter 0.2s ease, transform 0.1s ease;
    }}
    [data-testid="stBaseButton-primary"]:hover {{
        filter: brightness(1.1);
    }}
    [data-testid="stBaseButton-primary"]:active {{
        transform: translateY(1px);
    }}
    [class*="st-key-dash_card_"],
    [class*="st-key-req_card_"],
    .st-key-dash_action_bar {{
        background: {_card_bg} !important;
        backdrop-filter: blur(20px) saturate(180%);
        -webkit-backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid {_card_border} !important;
        box-shadow: {_card_shadow};
        border-radius: 12px !important;
    }}
    [data-testid="stMarkdownContainer"] {{
        line-height: 1.65;
        color: {_body_color};
    }}
    [data-testid="stMarkdownContainer"] strong {{
        color: {_body_color};
        font-weight: 600;
    }}
    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] * {{
        color: {_caption_color} !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

request_access = st.Page(
    "request_access_app.py",
    title="Request access",
    icon=":material/dashboard:",
    url_path="request",
)
access = st.Page(
    "access_app.py",
    title="Access requests",
    icon=":material/lock_open:",
    url_path="access",
)

st.navigation([request_access, access], position="hidden").run()
