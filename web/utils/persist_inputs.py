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
Persist last-used Home page inputs (topic, title, n_scenes, prompt_prefix, ...)
across app restarts / browser sessions.

Unlike st.session_state (which resets whenever the Streamlit process restarts
or a new browser session begins), this writes to a small local JSON file so
"last time's values" survive closing and reopening Pixelle-Video.

This mirrors the same pattern already used by pixelle_video.config.config_manager
for the System Configuration panel, just scoped to the Home page generation form.
"""

import json
from pathlib import Path
from typing import Any

from loguru import logger

_LAST_INPUTS_PATH = Path("data") / "last_inputs.json"


def load_last_inputs() -> dict[str, Any]:
    """Load last-used input values. Returns {} if none saved yet or on error."""
    try:
        if _LAST_INPUTS_PATH.exists():
            with open(_LAST_INPUTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load last_inputs.json: {e}")
    return {}


def save_last_inputs(values: dict[str, Any]) -> None:
    """Merge-save the given values into the persisted last-inputs file."""
    try:
        _LAST_INPUTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        current = load_last_inputs()
        current.update(values)
        with open(_LAST_INPUTS_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.warning(f"Failed to save last_inputs.json: {e}")
