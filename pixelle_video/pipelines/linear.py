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
Linear Video Pipeline Base Class

This module defines the template method pattern for linear video generation workflows.
It introduces `PipelineContext` for state management and `LinearVideoPipeline` for
process orchestration.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from loguru import logger

from pixelle_video.pipelines.base import BasePipeline
from pixelle_video.models.storyboard import (
    Storyboard,
    VideoGenerationResult,
    StoryboardConfig
)
from pixelle_video.models.progress import ProgressEvent


@dataclass
class PipelineContext:
    """
    Context object holding the state of a single pipeline execution.
    
    This object is passed between steps in the LinearVideoPipeline lifecycle.
    """
    # === Input ===
    input_text: str
    params: Dict[str, Any]
    progress_callback: Optional[Callable[[ProgressEvent], None]] = None
    
    # === Task State ===
    task_id: Optional[str] = None
    task_dir: Optional[str] = None
    
    # === Content ===
    title: Optional[str] = None
    narrations: List[str] = field(default_factory=list)
    
    # === Visuals ===
    image_prompts: List[Optional[str]] = field(default_factory=list)
    
    # === Configuration & Storyboard ===
    config: Optional[StoryboardConfig] = None
    storyboard: Optional[Storyboard] = None
    
    # === Output ===
    final_video_path: Optional[str] = None
    result: Optional[VideoGenerationResult] = None


class LinearVideoPipeline(BasePipeline):
    """
    Base class for linear video generation pipelines using the Template Method pattern.
    
    This class orchestrates the video generation process into distinct lifecycle steps:
    1. setup_environment
    2. generate_content
    3. determine_title
    4. plan_visuals
    5. initialize_storyboard
    6. produce_assets
    7. post_production
    8. finalize
    
    Subclasses should override specific steps to customize behavior while maintaining
    the overall workflow structure.
    """
    
    async def __call__(
        self,
        text: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        **kwargs
    ) -> VideoGenerationResult:
        """
        Execute the pipeline using the template method.
        """
        # 1. Initialize context
        ctx = PipelineContext(
            input_text=text,
            params=kwargs,
            progress_callback=progress_callback
        )
        
        try:
            # === Phase 1: Preparation ===
            await self.setup_environment(ctx)
            
            # === Phase 2: Content Creation ===
            await self.generate_content(ctx)
            await self.determine_title(ctx)
            
            # === Phase 3: Visual Planning ===
            await self.plan_visuals(ctx)
            await self.initialize_storyboard(ctx)
            
            # === Phase 4: Asset Production ===
            await self.produce_assets(ctx)
            
            # === Phase 5: Post Production ===
            await self.post_production(ctx)
            
            # === Phase 6: Finalization ===
            return await self.finalize(ctx)
            
        except Exception as e:
            await self.handle_exception(ctx, e)
            raise

    # ==================== Two-phase entry points (Review flow) ====================
    #
    # These let a caller (e.g. the Streamlit UI) stop right after all frames
    # (images/audio/video segments) are produced, let the user inspect/regenerate
    # individual frames, and only THEN compose the final video.
    #
    # generate_until_review() runs phases 1-4 (everything up to and including
    # produce_assets) and returns the PipelineContext instead of a finished video.
    # compose_and_finalize() takes that same context and runs the remaining
    # phases (post_production + finalize) to produce the final video.
    #
    # The original __call__ above is untouched, so batch mode / API usage that
    # doesn't need a review step keeps working exactly as before.

    async def generate_until_review(
        self,
        text: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None,
        **kwargs
    ) -> PipelineContext:
        """
        Run the pipeline up through asset production (all frames generated:
        image/video + audio for each scene), then stop BEFORE composing the
        final video. Returns the PipelineContext so the caller can inspect
        ctx.storyboard.frames, let the user regenerate individual frames via
        regenerate_frame(), and later call compose_and_finalize(ctx).
        """
        ctx = PipelineContext(
            input_text=text,
            params=kwargs,
            progress_callback=progress_callback
        )

        try:
            # === Phase 1: Preparation ===
            await self.setup_environment(ctx)

            # === Phase 2: Content Creation ===
            await self.generate_content(ctx)
            await self.determine_title(ctx)

            # === Phase 3: Visual Planning ===
            await self.plan_visuals(ctx)
            await self.initialize_storyboard(ctx)

            # === Phase 4: Asset Production ===
            await self.produce_assets(ctx)

            return ctx

        except Exception as e:
            await self.handle_exception(ctx, e)
            raise

    async def compose_and_finalize(self, ctx: PipelineContext) -> VideoGenerationResult:
        """
        Resume a pipeline run previously paused by generate_until_review(),
        composing the final video from whatever frames are currently in
        ctx.storyboard.frames (after any per-frame review/regeneration) and
        producing the VideoGenerationResult.
        """
        try:
            # === Phase 5: Post Production ===
            await self.post_production(ctx)

            # === Phase 6: Finalization ===
            return await self.finalize(ctx)

        except Exception as e:
            await self.handle_exception(ctx, e)
            raise
    
    async def setup_environment(self, ctx: PipelineContext):
        """Step 1: Setup task directory and environment."""
        pass
        
    async def generate_content(self, ctx: PipelineContext):
        """Step 2: Generate or process script/narrations."""
        pass
        
    async def determine_title(self, ctx: PipelineContext):
        """Step 3: Determine or generate video title."""
        pass
        
    async def plan_visuals(self, ctx: PipelineContext):
        """Step 4: Generate image prompts or visual descriptions."""
        pass
        
    async def initialize_storyboard(self, ctx: PipelineContext):
        """Step 5: Create Storyboard object and frames."""
        pass
        
    async def produce_assets(self, ctx: PipelineContext):
        """Step 6: Generate audio, images, and render frames (Core processing)."""
        pass
        
    async def post_production(self, ctx: PipelineContext):
        """Step 7: Concatenate videos and add BGM."""
        pass
        
    async def finalize(self, ctx: PipelineContext) -> VideoGenerationResult:
        """Step 8: Create result object and persist metadata."""
        raise NotImplementedError("finalize must be implemented by subclass")

    async def handle_exception(self, ctx: PipelineContext, error: Exception):
        """Handle exceptions during pipeline execution."""
        logger.error(f"Pipeline execution failed: {error}")
