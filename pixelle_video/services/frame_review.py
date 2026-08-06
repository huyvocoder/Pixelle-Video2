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
Frame Review Helpers

Utilities for the "review before compose" flow: regenerating a single
storyboard frame (image, and optionally its voice) without touching any
other frame, and without re-running the whole pipeline.

Relies on FrameProcessor's existing behavior:
- If frame.audio_path is already set, it will NOT regenerate audio.
- If frame.image_prompt is set, it WILL (re)generate the image/video and
  recompose it, since it doesn't check whether image_path is already set.

So to regenerate just the image of a frame, we simply clear its previously
generated media paths (keeping audio_path untouched) and call the frame
processor again on that single frame.
"""

from typing import Optional

from loguru import logger

from pixelle_video.models.storyboard import Storyboard, StoryboardFrame


async def regenerate_frame(
    core,
    storyboard: Storyboard,
    frame_index: int,
    regenerate_voice: bool = False,
) -> StoryboardFrame:
    """
    Regenerate a single frame's image (and optionally its voice) in place.

    Args:
        core: PixelleVideoCore instance (has .frame_processor)
        storyboard: The Storyboard containing the frame (mutated in place)
        frame_index: 0-based index of the frame to regenerate
        regenerate_voice: If True, also clear+regenerate the narration audio.
                           If False (default), the existing audio is reused
                           and only the image is regenerated.

    Returns:
        The updated StoryboardFrame (same object as storyboard.frames[frame_index])
    """
    if frame_index < 0 or frame_index >= len(storyboard.frames):
        raise IndexError(f"frame_index {frame_index} out of range (0-{len(storyboard.frames) - 1})")

    frame = storyboard.frames[frame_index]

    logger.info(f"🔄 Regenerating frame {frame_index} (voice={'yes' if regenerate_voice else 'no'})")

    # Clear previously generated media so FrameProcessor treats this as "needs generation" again.
    frame.image_path = None
    frame.video_path = None
    frame.composed_image_path = None
    frame.video_segment_path = None

    if regenerate_voice:
        frame.audio_path = None
        frame.duration = 0.0

    updated_frame = await core.frame_processor(
        frame=frame,
        storyboard=storyboard,
        config=storyboard.config,
        total_frames=len(storyboard.frames),
    )

    storyboard.frames[frame_index] = updated_frame
    logger.info(f"✅ Frame {frame_index} regenerated")

    return updated_frame
