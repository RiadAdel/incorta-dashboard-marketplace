import streamlit as st
import streamlit.components.v1 as components


def apply_theme() -> str:
    """Render the logo, theme toggle, and page-wide CSS. Returns 'dark' or 'light'."""
    theme = getattr(getattr(st.context, "theme", None), "type", "dark") or "dark"

    logo_path = (
        "static/incorta-logo-dark.svg" if theme == "light" else "static/incorta-logo.svg"
    )

    _, logo_col, toggle_col = st.columns([1, 4, 1], vertical_alignment="center")
    with logo_col.container(horizontal_alignment="center"):
        st.image(logo_path, width=280)
    with toggle_col.container(horizontal=True, horizontal_alignment="right"):
        label, tooltip = (
            (":material/light_mode:", "Switch to light mode")
            if theme == "dark"
            else (":material/dark_mode:", "Switch to dark mode")
        )
        if st.button(label, key="theme_toggle", help=tooltip):
            new_theme = "light" if theme == "dark" else "dark"
            js_value = "Dark" if new_theme == "dark" else "Light"
            components.html(
                f"""
                <script>
                    const value = JSON.stringify("{js_value}");
                    const path = window.parent.location.pathname;
                    window.parent.localStorage.setItem(`stActiveTheme-${{path}}-v2`, value);
                    window.parent.location.reload();
                </script>
                """,
                height=0,
            )
            st.stop()

    if theme == "dark":
        bg = (
            "radial-gradient(ellipse at top left, #1a2f6e 0%, transparent 55%),"
            "radial-gradient(ellipse at bottom right, #1e3a8a 0%, transparent 55%),"
            "linear-gradient(135deg, #070c1a 0%, #0d1740 100%)"
        )
        title_color = "#bfdbfe"
        card_bg = "rgba(255, 255, 255, 0.05)"
        card_border = "rgba(59, 130, 246, 0.2)"
        card_shadow = "0 8px 32px rgba(0, 0, 0, 0.35)"
        caption_color = "#93c5fd"
        body_color = "#e0f2fe"
        btn_grad = "linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)"
    else:
        bg = (
            "radial-gradient(ellipse at top left, #dbeafe 0%, transparent 55%),"
            "radial-gradient(ellipse at bottom right, #fef3c7 0%, transparent 55%),"
            "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)"
        )
        title_color = "#0f172a"
        card_bg = "rgba(255, 255, 255, 0.85)"
        card_border = "rgba(30, 64, 175, 0.15)"
        card_shadow = "0 8px 32px rgba(30, 64, 175, 0.08)"
        caption_color = "#2563eb"
        body_color = "#1e3a8a"
        btn_grad = "linear-gradient(135deg, #1e40af 0%, #2563eb 100%)"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fira+Sans:wght@300;400;500;600;700&display=swap');

        html, body, [data-testid="stAppViewContainer"], [data-testid="stMarkdownContainer"],
        [data-testid="stText"], button, input, textarea, select {{
            font-family: 'Fira Sans', sans-serif !important;
        }}
        [data-testid="stAppViewContainer"] {{
            background: {bg} fixed;
        }}
        [data-testid="stHeader"] {{
            background: transparent;
        }}
        [data-testid="stHeading"] h1,
        [data-testid="stHeading"] h2 {{
            color: {title_color} !important;
            -webkit-text-fill-color: {title_color} !important;
        }}
        [data-testid="stBaseButton-primary"] {{
            background: {btn_grad} !important;
            border: none !important;
            color: #ffffff !important;
            font-family: 'Fira Sans', sans-serif !important;
            font-weight: 600 !important;
            letter-spacing: 0.01em;
            transition: filter 0.2s ease, transform 0.1s ease;
        }}
        [data-testid="stBaseButton-primary"] p {{
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }}
        [data-testid="stBaseButton-primary"]:hover {{
            filter: brightness(1.12);
        }}
        [data-testid="stBaseButton-primary"]:active {{
            transform: translateY(1px);
        }}
        [data-testid="stBaseButton-primary"]:disabled,
        [data-testid="stBaseButton-primary"][aria-disabled="true"] {{
            opacity: 0.45 !important;
            filter: none !important;
            cursor: not-allowed !important;
        }}
        @media (prefers-reduced-motion: reduce) {{
            [data-testid="stBaseButton-primary"],
            [class*="st-key-dash_card_"],
            [class*="st-key-req_card_"],
            .st-key-dash_action_bar {{
                transition: none !important;
            }}
        }}
        [class*="st-key-dash_card_"],
        [class*="st-key-req_card_"],
        .st-key-dash_action_bar {{
            background: {card_bg} !important;
            backdrop-filter: blur(20px) saturate(160%);
            -webkit-backdrop-filter: blur(20px) saturate(160%);
            border: 1px solid {card_border} !important;
            box-shadow: {card_shadow};
            border-radius: 12px !important;
            transition: box-shadow 0.2s ease;
        }}
        [class*="st-key-dash_card_"]:hover,
        [class*="st-key-req_card_"]:hover {{
            box-shadow: {card_shadow.replace("0.35", "0.5").replace("0.08", "0.14")};
        }}
        [data-testid="stMarkdownContainer"] {{
            line-height: 1.65;
            color: {body_color};
        }}
        [data-testid="stMarkdownContainer"] strong {{
            color: {body_color};
            font-weight: 600;
        }}
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] * {{
            color: {caption_color} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    return theme
