# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Home Page - Main video generation interface
"""

import sys
from pathlib import Path

# Add project root to sys.path
_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

# Import state management
from web.state.session import init_session_state, init_i18n, get_pixelle_video

# Import components
from web.components.header import render_header
from web.components.faq import render_faq_sidebar

# Page config
st.set_page_config(
    page_title="Home - Pixelle-Video",
    page_icon=":material/home:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    """Main UI entry point"""
    # Initialize session state and i18n
    init_session_state()
    init_i18n()

    # ========================================================================
    # Global visual pass: less wasted padding, flatten the "box inside a box"
    # look (outer settings panel + inner per-section containers both had a
    # full border, reading as cluttered/uneven) into a single clean panel
    # with subtle section dividers instead.
    # ========================================================================
    st.markdown(
        """
        <style>
        :root {
            --pxv-bg-main: #0b0f19;
            --pxv-card-bg: #111827;
            --pxv-accent: #06b6d4;
            --pxv-accent-hover: #22d3ee;
            --pxv-accent-transparent: rgba(6, 182, 212, 0.15);
            --pxv-text-primary: #e2e8f0;
            --pxv-text-secondary: #94a3b8;
            --pxv-border: #1e293b;
            --pxv-border-active: #06b6d4;
            --pxv-radius: 8px;
            --pxv-radius-sm: 4px;
        }

        /* Basic typography setup - SMALLER, CRISPER */
        p, h1, h2, h3, h4, h5, h6, label, li, span, div, input, textarea, button {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 13px !important;
            color: var(--pxv-text-primary);
        }
        
        .stApp {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--pxv-bg-main);
        }

        /* ── Prevent full-page scroll ──────────────────────────────────────── */
        html { overflow: hidden !important; }
        body { overflow: hidden !important; height: 100vh !important; }

        /* stMain is Streamlit's actual scrolling wrapper — lock it            */
        section[data-testid="stMain"] {
            overflow: hidden !important;
        }
        section[data-testid="stMain"] > div:first-child {
            overflow: hidden !important;
            height: 100% !important;
        }

        /* Strip Streamlit's huge default padding (catches emotion-cache classes) */
        .block-container,
        [class*="block-container"] {
            padding-top: 3rem !important;
            padding-bottom: 0.25rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
            max-width: 100% !important;
            min-width: auto !important;
        }
        @media (min-width: 0px) {
            .block-container, [class*="block-container"] {
                padding-left: 1.5rem !important;
                padding-right: 1.5rem !important;
            }
        }

        /* ── Fixed left column, flex-fill right column ─────────────────────── */
        div[data-testid="stHorizontalBlock"] {
            align-items: stretch;
            gap: 1rem;
        }
        /* Left (settings) column — fixed 360px, never shrinks */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:first-child {
            min-width: 340px !important;
            max-width: 340px !important;
            flex: 0 0 340px !important;
        }
        /* Right (results) column — takes all remaining space */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child {
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }

        /* ── Columns: no overflow interference ─────────────────────────────── */
        div[data-testid="column"] {
            overflow: visible !important;
        }

        /* ── Panel scroll container: override Streamlit's hardcoded height ─── */
        /* st.container(height=X) creates a div with inline style="height:Xpx;  */
        /* overflow-y:auto". We override just the height with a viewport calc.   */
        /* Offset: 38px toolbar + 44px nav + 3rem padding(48px) + 12px = 142px  */
        div[data-testid="stLayoutWrapper"][overflow="auto"]{
            height: calc(100vh - 80px) !important;
            max-height: calc(100vh - 80px) !important;
        }

        div[data-testid="stLayoutWrapper"][overflow="auto"] > div[data-testid="stVerticalBlock"]{
            border-radius: var(--pxv-radius);
            border:1px solid var(--pxv-border);
            background:var(--pxv-card-bg);
            padding:1rem;
        }

        /* Inner nested containers (expanders, sub-containers): free height */
        div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {
            height: auto !important;
            overflow: visible !important;
            background-color: #0b0f19 !important;
            border: 1px solid var(--pxv-border) !important;
            padding: 0.75rem !important;
            margin-bottom: 0.5rem;
            box-shadow: none;
        }


        /* Headings - NOT HUGE */
        h1, h2, h3, h4, h5, h6 {
            color: var(--pxv-text-primary) !important;
            font-weight: 600 !important;
            letter-spacing: 0;
        }
        .block-container h1 {
            font-size: 18px !important;
            margin-bottom: 0.5rem !important;
            color: var(--pxv-accent) !important;
        }

        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #0b0f19 !important;
            border-right: 1px solid var(--pxv-border);
        }
        
        section[data-testid="stSidebar"] div[data-testid="stPageLink-NavLink"],
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"] {
            border-radius: var(--pxv-radius-sm) !important;
            margin-bottom: 2px;
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        section[data-testid="stSidebar"] div[data-testid="stPageLink-NavLink"][aria-current="page"],
        section[data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][aria-current="page"] {
            background-color: var(--pxv-accent-transparent) !important;
            border-left: 2px solid var(--pxv-accent);
        }

        /* Inputs (Text, Number, Textarea) - THIN CYAN BORDERS ON FOCUS */
        div[data-testid="stTextInput"] input,
        div[data-testid="stTextArea"] textarea,
        div[data-testid="stNumberInput"] input {
            background-color: #0b0f19 !important;
            border: 1px solid var(--pxv-border) !important;
            border-radius: var(--pxv-radius-sm) !important;
            color: var(--pxv-text-primary) !important;
            padding: 0.5rem 0.75rem !important;
        }

        div[data-testid="stTextInput"] input:focus,
        div[data-testid="stTextArea"] textarea:focus,
        div[data-testid="stNumberInput"] input:focus {
            border-color: var(--pxv-accent) !important;
            box-shadow: 0 0 5px var(--pxv-accent-transparent) !important;
        }

        /* Select / Dropdown */
        div[data-testid="stSelectbox"] > div,
        div[data-baseweb="select"] > div {
            background-color: #0b0f19 !important;
            border: 1px solid var(--pxv-border) !important;
            border-radius: var(--pxv-radius-sm) !important;
        }

        /* Buttons */
        div[data-testid="stButton"] button {
            border-radius: var(--pxv-radius-sm) !important;
            font-weight: 500;
            border: 1px solid var(--pxv-border) !important;
            background-color: #1e293b !important;
            transition: all 0.2s ease;
        }
        div[data-testid="stButton"] button:hover {
            border-color: var(--pxv-text-secondary) !important;
            background-color: #334155 !important;
        }
        div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(90deg, #06b6d4 0%, #3b82f6 100%) !important;
            border: none !important;
            color: white !important;
            font-weight: 600;
            box-shadow: 0 4px 10px rgba(6, 182, 212, 0.3);
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            box-shadow: 0 4px 15px rgba(6, 182, 212, 0.5);
            opacity: 0.9;
        }

        /* Background */
        div[data-testid="stProgress"]{
            width:100%;
        }

        div[data-testid="stProgress"] > div{
            border-radius:999px;
            overflow:hidden;
        }

        /* Track */
        div[data-testid="stProgress"] > div > div:first-child{
            background:#1e293b !important;
        }

        /* Fill */
        div[data-testid="stProgress"] div[role="progressbar"]{
            background:#06b6d4 !important;
        }

        /* Expanders */
        div[data-testid="stExpander"] {
            border-radius: var(--pxv-radius-sm) !important;
            border: 1px solid var(--pxv-border) !important;
            background-color: transparent !important;
        }
        
        /* Form item labels */
        label[data-testid="stWidgetLabel"] p {
            color: var(--pxv-text-secondary) !important;
            font-size: 12px !important;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* Custom Panel Header */
        .panel-header {
            font-size: 14px;
            font-weight: 600;
            color: var(--pxv-accent);
            border-bottom: 1px solid var(--pxv-border);
            padding-bottom: 8px;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Render header (title + language selector)
    # render_header()  # Removed per user request

    # Render FAQ in sidebar
    render_faq_sidebar()

    # Initialize Pixelle-Video
    pixelle_video = get_pixelle_video()

    # ========================================================================
    # Pipeline: only Quick Create is active right now. Other pipelines
    # (Custom Media, Digital Human, Image To Video, Action Transfer) are
    # temporarily hidden - not deleted, just not shown - until they're
    # revisited. Render Quick Create directly, no tab bar needed for a
    # single pipeline.
    #
    # System Configuration now lives as its own sidebar page (see
    # web/pages/3_⚙️_Settings.py) instead of sharing this screen.
    # ========================================================================
    from web.pipelines import get_pipeline_ui

    quick_create = get_pipeline_ui("quick_create")
    if quick_create is not None:
        quick_create.render(pixelle_video)
    else:
        # Fallback: if quick_create isn't registered for some reason, don't
        # silently show nothing - fall back to the old tabbed view so the
        # app is never left blank.
        from web.pipelines import get_all_pipeline_uis
        pipelines = get_all_pipeline_uis()
        tab_labels = [f"{p.icon} {p.display_name}" for p in pipelines]
        tabs = st.tabs(tab_labels)
        for i, pipeline in enumerate(pipelines):
            with tabs[i]:
                if pipeline.description:
                    st.caption(pipeline.description)
                pipeline.render(pixelle_video)


if __name__ == "__main__":
    main()

