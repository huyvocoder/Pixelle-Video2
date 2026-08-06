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
Content input components for web UI (left column)
"""

import streamlit as st

from web.i18n import tr
from web.utils.async_helpers import get_project_version
from web.utils.persist_inputs import load_last_inputs


def render_content_input():
    """Render content input section (left column) with batch support"""
    last = load_last_inputs()

    with st.expander(tr('section.content_input'), expanded=False):
        
        # ====================================================================
        # Step 1: Batch mode toggle (highest priority)
        # ====================================================================
        batch_mode = st.checkbox(
            tr("batch.mode_label"),
            value=False,
            help=tr("batch.mode_help")
        )
        
        if not batch_mode:
            # ================================================================
            # Single task mode (original logic, unchanged)
            # ================================================================
            # Processing mode selection
            mode_options = ["generate", "fixed"]
            saved_mode = last.get("mode", "generate")
            mode = st.radio(
                "Processing Mode",
                mode_options,
                index=mode_options.index(saved_mode) if saved_mode in mode_options else 0,
                horizontal=True,
                format_func=lambda x: tr(f"mode.{x}"),
                label_visibility="collapsed"
            )
            
            # Text input (unified for both modes)
            text_placeholder = tr("input.topic_placeholder") if mode == "generate" else tr("input.content_placeholder")
            text_height = 120 if mode == "generate" else 200
            text_help = tr("input.text_help_generate") if mode == "generate" else tr("input.text_help_fixed")
            
            text = st.text_area(
                tr("input.text"),
                value=last.get("text", ""),
                placeholder=text_placeholder,
                height=text_height,
                help=text_help
            )
            
            # Narrative style toggle: only relevant for "generate" mode, since
            # the AI writes the whole script from scratch there. In "fixed"
            # mode the user supplies their own content, so restructuring it
            # into a character story doesn't apply.
            if mode == "generate":
                narrative_options = {
                    "standard": "📋 Liệt kê / lời khuyên",
                    "character_story": "🎭 Kể chuyện nhân vật",
                }
                narrative_keys = list(narrative_options.keys())
                saved_narrative_mode = last.get("narrative_mode", "standard")
                narrative_mode = st.radio(
                    "Narrative Style",
                    options=narrative_keys,
                    index=narrative_keys.index(saved_narrative_mode) if saved_narrative_mode in narrative_keys else 0,
                    format_func=lambda x: narrative_options[x],
                    horizontal=True,
                    label_visibility="collapsed",
                    help="Liệt kê: nêu lời khuyên trực tiếp. Kể chuyện nhân vật: kể qua hành trình của 1 nhân vật giả định, thường thu hút hơn."
                )
            else:
                narrative_mode = "standard"
            
            # Split mode selector (only show in fixed mode)
            if mode == "fixed":
                split_mode_options = {
                    "paragraph": tr("split.mode_paragraph"),
                    "line": tr("split.mode_line"),
                    "sentence": tr("split.mode_sentence"),
                }
                split_mode_keys = list(split_mode_options.keys())
                saved_split_mode = last.get("split_mode", "paragraph")
                split_mode = st.selectbox(
                    tr("split.mode_label"),
                    options=split_mode_keys,
                    format_func=lambda x: split_mode_options[x],
                    index=split_mode_keys.index(saved_split_mode) if saved_split_mode in split_mode_keys else 0,
                    help=tr("split.mode_help")
                )
            else:
                split_mode = "paragraph"  # Default for generate mode (not used)
            
            # Title input (optional for both modes)
            title = st.text_input(
                tr("input.title"),
                value=last.get("title", ""),
                placeholder=tr("input.title_placeholder"),
                help=tr("input.title_help")
            )
            
            # Number of scenes (only show in generate mode)
            if mode == "generate":
                n_scenes = st.number_input(
                    tr("video.frames"),
                    min_value=3,
                    max_value=400,
                    value=int(last.get("n_scenes", 5)),
                    step=1,
                    help=tr("video.frames_help") + " (tối đa 400 cảnh)"
                )
                st.caption(tr("video.frames_label", n=n_scenes))
            else:
                # Fixed mode: n_scenes is ignored, set default value.
                # NOTE: in "fixed" mode the real scene count depends on how
                # the pasted text gets split (paragraph/line/sentence) and is
                # only known after the backend splits it - it can easily be
                # in the hundreds too. So the rest controls below are shown
                # unconditionally rather than gated on this placeholder value.
                n_scenes = 5
                st.info(tr("video.frames_fixed_mode_hint"))

            # GPU rest controls - shown for BOTH modes (generate and fixed),
            # since a long "fixed" script split into many scenes is just as
            # likely to run the GPU for hours as a long "generate" video.
            # Fixed, mode-independent threshold (not based on an estimated
            # n_scenes, which isn't reliably known in fixed mode).
            with st.expander("🌡️ Nghỉ định kỳ (khuyên dùng cho video dài)", expanded=False):
                st.caption(
                    "Cho máy nghỉ vài giây sau mỗi N cảnh để hạ nhiệt GPU, "
                    "tránh chạy full tải liên tục nhiều giờ."
                )
                rest_enabled = st.checkbox(
                    "Bật nghỉ định kỳ",
                    value=bool(last.get("rest_enabled", False)),
                    key="rest_enabled_checkbox"
                )
                if rest_enabled:
                    rest_col1, rest_col2 = st.columns(2)
                    with rest_col1:
                        rest_every_n = st.number_input(
                            "Nghỉ sau mỗi (cảnh)",
                            min_value=2,
                            max_value=100,
                            value=max(2, int(last.get("rest_every_n", 10)) or 10),
                            step=1,
                            key="rest_every_n_input"
                        )
                    with rest_col2:
                        rest_seconds = st.number_input(
                            "Thời gian nghỉ (giây)",
                            min_value=5,
                            max_value=300,
                            value=max(5, int(last.get("rest_seconds", 30)) or 30),
                            step=5,
                            key="rest_seconds_input"
                        )
                else:
                    rest_every_n = 0
                    rest_seconds = 0

            return {
                "batch_mode": False,
                "mode": mode,
                "text": text,
                "title": title,
                "n_scenes": n_scenes,
                "split_mode": split_mode,
                "narrative_mode": narrative_mode,
                "rest_every_n": rest_every_n if rest_enabled else 0,
                "rest_seconds": rest_seconds if rest_enabled else 0
            }
        
        else:
            # ================================================================
            # Batch mode (simplified YAGNI version)
            # ================================================================
            st.markdown(f"**{tr('batch.section_title')}**")
            
            # Batch rules info
            st.info(f"""
**{tr('batch.rules_title')}**
- ✅ {tr('batch.rule_1')}
- ✅ {tr('batch.rule_2')}
- ✅ {tr('batch.rule_3')}
            """)
            
            # Batch topics input
            text_input = st.text_area(
                tr("batch.topics_label"),
                height=300,
                placeholder=tr("batch.topics_placeholder"),
                help=tr("batch.topics_help")
            )
            
            # Split topics by newline
            if text_input:
                # Simple split by newline, filter empty lines
                topics = [
                    line.strip() 
                    for line in text_input.strip().split('\n') 
                    if line.strip()
                ]
                
                if topics:
                    # Check count limit
                    if len(topics) > 100:
                        st.error(tr("batch.count_error", count=len(topics)))
                        topics = []
                    else:
                        st.success(tr("batch.count_success", count=len(topics)))
                        
                        # Preview topics list
                        with st.expander(tr("batch.preview_title"), expanded=False):
                            for i, topic in enumerate(topics, 1):
                                st.markdown(f"`{i}.` {topic}")
                else:
                    topics = []
            else:
                topics = []
            
            st.markdown("---")
            
            # Title prefix (optional)
            title_prefix = st.text_input(
                tr("batch.title_prefix_label"),
                placeholder=tr("batch.title_prefix_placeholder"),
                help=tr("batch.title_prefix_help")
            )
            
            # Number of scenes (unified for all videos)
            n_scenes = st.slider(
                tr("batch.n_scenes_label"),
                min_value=3,
                max_value=30,
                value=5,
                help=tr("batch.n_scenes_help")
            )
            st.caption(tr("batch.n_scenes_caption", n=n_scenes))
            
            # Config info
            st.info(f"📌 {tr('batch.config_info')}")
            
            return {
                "batch_mode": True,
                "topics": topics,
                "mode": "generate",  # Fixed to AI generate content
                "title_prefix": title_prefix,
                "n_scenes": n_scenes,
            }


def render_bgm_section(key_prefix=""):
    """Render BGM selection section"""
    with st.expander(tr('section.bgm'), expanded=False):
        
        with st.expander(tr("help.feature_description"), expanded=False):
            st.markdown(f"**{tr('help.what')}**")
            st.markdown(tr("bgm.what"))
            st.markdown(f"**{tr('help.how')}**")
            st.markdown(tr("bgm.how"))
        
        # Dynamically scan bgm folder for music files (merged from bgm/ and data/bgm/)
        from pixelle_video.utils.os_util import list_resource_files
        
        try:
            all_files = list_resource_files("bgm")
            # Filter to audio files only
            audio_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg')
            bgm_files = sorted([f for f in all_files if f.lower().endswith(audio_extensions)])
        except Exception as e:
            st.warning(f"Failed to load BGM files: {e}")
            bgm_files = []
        
        # Add special "None" option
        bgm_options = [tr("bgm.none")] + bgm_files
        
        # Default to "default.mp3" if exists, otherwise first option
        default_index = 0
        if "default.mp3" in bgm_files:
            default_index = bgm_options.index("default.mp3")
        
        bgm_choice = st.selectbox(
            "BGM",
            bgm_options,
            index=default_index,
            label_visibility="collapsed",
            key=f"{key_prefix}bgm_selector"
        )
        
        # BGM volume slider (only show when BGM is selected)
        if bgm_choice != tr("bgm.none"):
            bgm_volume = st.slider(
                tr("bgm.volume"),
                min_value=0.0,
                max_value=0.5,
                value=0.2,
                step=0.01,
                format="%.2f",
                key=f"{key_prefix}bgm_volume_slider",
                help=tr("bgm.volume_help")
            )
        else:
            bgm_volume = 0.2  # Default value when no BGM selected
        
        # BGM preview button (only if BGM is not "None")
        if bgm_choice != tr("bgm.none"):
            if st.button(tr("bgm.preview"), key=f"{key_prefix}preview_bgm", use_container_width=True):
                from pixelle_video.utils.os_util import get_resource_path, resource_exists
                try:
                    if resource_exists("bgm", bgm_choice):
                        bgm_file_path = get_resource_path("bgm", bgm_choice)
                        st.audio(bgm_file_path)
                    else:
                        st.error(tr("bgm.preview_failed", file=bgm_choice))
                except Exception as e:
                    st.error(f"{tr('bgm.preview_failed', file=bgm_choice)}: {e}")
        
        # Use full filename for bgm_path (including extension)
        bgm_path = None if bgm_choice == tr("bgm.none") else bgm_choice
    
    return {
        "bgm_path": bgm_path,
        "bgm_volume": bgm_volume
    }


def render_version_info():
    """Render version info and GitHub link"""
    with st.container(border=False):
        st.markdown(f"**{tr('version.title')}**")
        version = get_project_version()
        github_url = "https://github.com/AIDC-AI/Pixelle-Video"
        
        # Version and GitHub link in one line
        github_url = "https://github.com/AIDC-AI/Pixelle-Video"
        badge_url = "https://img.shields.io/github/stars/AIDC-AI/Pixelle-Video"

        st.markdown(
            f'{tr("version.current")}: `{version}` &nbsp;&nbsp; '
            f'<a href="{github_url}" target="_blank">'
            f'<img src="{badge_url}" alt="GitHub stars" style="vertical-align: middle;">'
            f'</a>',
            unsafe_allow_html=True)

