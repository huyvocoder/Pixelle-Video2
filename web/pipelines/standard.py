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
Standard Pipeline UI

Implements a 2-panel fixed-height layout for the Standard Pipeline:
left panel holds all settings (scrolls independently), right panel
holds generation results (scrolls independently).
"""

import streamlit as st
from typing import Any
from web.i18n import tr

from web.pipelines.base import PipelineUI, register_pipeline_ui

# Import components
from web.components.content_input import render_content_input, render_bgm_section, render_version_info
from web.components.style_config import render_style_config
from web.components.output_preview import render_output_preview


class StandardPipelineUI(PipelineUI):
    """
    UI for the Standard Video Generation Pipeline.
    Implements a 2-panel fixed-height layout (settings left, results right),
    each scrolling independently.
    """
    name = "quick_create"
    icon = "⚡"
    
    @property
    def display_name(self):
        return tr("pipeline.quick_create.name")
    
    @property
    def description(self):
        return tr("pipeline.quick_create.description")
    
    def render(self, pixelle_video: Any):
        # Use height=700 as a placeholder — CSS overrides it with calc(100vh - X)
        # so it adapts to any screen size. Streamlit's height= creates a native
        # scroll container which CSS can then adjust.
        PANEL_HEIGHT = 700

        settings_col, results_col = st.columns([1, 2])

        with settings_col:
            with st.container(height=PANEL_HEIGHT, border=True):
                st.markdown("<div class='panel-header'>⚙️ CẤU HÌNH VIDEO</div>", unsafe_allow_html=True)

                content_params = render_content_input()
                bgm_params = render_bgm_section()
                style_params = render_style_config(pixelle_video)

        with results_col:
            with st.container(height=PANEL_HEIGHT, border=True):
                st.markdown("<div class='panel-header'>🎬 KẾT QUẢ TRỰC QUAN</div>", unsafe_allow_html=True)

                video_params = {
                    "pipeline": self.name,
                    **content_params,
                    **bgm_params,
                    **style_params
                }

                render_output_preview(pixelle_video, video_params)




# Register self
register_pipeline_ui(StandardPipelineUI)
