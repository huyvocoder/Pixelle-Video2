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
Settings Page - System Configuration (LLM + ComfyUI)

Lives as its own sidebar entry (next to Home/History) instead of sharing
space with the Home screen, so it opens directly on click.
"""

import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
_project_root = _script_dir.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import streamlit as st

from web.state.session import init_session_state, init_i18n
from web.components.header import render_header
from web.components.settings import render_advanced_settings

st.set_page_config(
    page_title="Settings",
    page_icon=":material/settings:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def main():
    init_session_state()
    init_i18n()

    render_header()
    render_advanced_settings()


if __name__ == "__main__":
    main()
