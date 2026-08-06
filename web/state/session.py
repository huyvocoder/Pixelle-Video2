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
Session state management for web UI
"""

import streamlit as st
from loguru import logger

from web.i18n import get_language, set_language
from web.utils.async_helpers import run_async


def init_session_state():
    """Initialize session state variables"""
    if "language" not in st.session_state:
        # Use auto-detected system language
        st.session_state.language = get_language()


def init_i18n():
    """Initialize internationalization"""
    # Locales are already loaded and system language detected on import
    # Get language from session state or use auto-detected system language
    if "language" not in st.session_state:
        st.session_state.language = get_language()  # Use auto-detected language
    
    # Set current language
    set_language(st.session_state.language)


def get_pixelle_video():
    """
    Get initialized Pixelle-Video instance with proper caching and cleanup
    
    Uses st.session_state to cache the instance per user session.
    ComfyKit is lazily initialized and automatically recreated on config changes.
    """
    from pixelle_video.service import PixelleVideoCore
    from pixelle_video.config import config_manager
    
    # Compute config hash for change detection
    import hashlib
    import json
    config_dict = config_manager.config.to_dict()
    # Only track ComfyUI config for hash (other config changes don't need core recreation)
    comfyui_config = config_dict.get("comfyui", {})
    config_hash = hashlib.md5(json.dumps(comfyui_config, sort_keys=True).encode()).hexdigest()
    
    # Check if we need to create or recreate core instance
    need_recreate = False
    if 'pixelle_video' not in st.session_state:
        need_recreate = True
        logger.info("Creating new PixelleVideoCore instance (first time)")
    elif st.session_state.get('pixelle_video_config_hash') != config_hash:
        need_recreate = True
        logger.info("Configuration changed, recreating PixelleVideoCore instance")
        # Cleanup old instance
        old_core = st.session_state.pixelle_video
        try:
            run_async(old_core.cleanup())
        except Exception as e:
            logger.warning(f"Failed to cleanup old PixelleVideoCore: {e}")
    
    if need_recreate:
        # Create and initialize new instance
        pixelle_video = PixelleVideoCore()
        run_async(pixelle_video.initialize())
        
        # Cache in session state
        st.session_state.pixelle_video = pixelle_video
        st.session_state.pixelle_video_config_hash = config_hash
        logger.info("✅ PixelleVideoCore initialized and cached")
    else:
        pixelle_video = st.session_state.pixelle_video
        logger.debug("Reusing cached PixelleVideoCore instance")
    
    return pixelle_video

