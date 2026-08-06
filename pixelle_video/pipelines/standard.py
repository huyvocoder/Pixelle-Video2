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
Standard Video Generation Pipeline

Standard workflow for generating short videos from topic or fixed script.
This is the default pipeline for general-purpose video generation.
Refactored to use LinearVideoPipeline (Template Method Pattern).
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, Literal, List
import asyncio
import shutil

from loguru import logger

from pixelle_video.pipelines.linear import LinearVideoPipeline, PipelineContext
from pixelle_video.models.progress import ProgressEvent
from pixelle_video.models.storyboard import (
    Storyboard,
    StoryboardFrame,
    StoryboardConfig,
    ContentMetadata,
    VideoGenerationResult
)
from pixelle_video.utils.content_generators import (
    generate_title,
    generate_narrations_from_topic,
    split_narration_script,
    generate_image_prompts,
)
from pixelle_video.utils.os_util import (
    create_task_output_dir,
    get_task_final_video_path
)
from pixelle_video.utils.template_util import get_template_type
from pixelle_video.utils.prompt_helper import build_image_prompt
from pixelle_video.services.video import VideoService


def _format_srt_timestamp(seconds: float) -> str:
    """Format a number of seconds as an SRT timestamp: HH:MM:SS,mmm"""
    if seconds < 0:
        seconds = 0.0
    total_ms = int(round(seconds * 1000))
    hours, rem_ms = divmod(total_ms, 3_600_000)
    minutes, rem_ms = divmod(rem_ms, 60_000)
    secs, ms = divmod(rem_ms, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _write_srt_file(storyboard: "Storyboard", video_output_path: str) -> Optional[str]:
    """
    Write a standard .srt subtitle file next to the final video, one entry
    per frame, using each frame's real duration (already exact - the video
    segment for that frame is forced to match its audio duration exactly in
    VideoService.create_video_from_image) to compute cumulative timestamps.

    This lets timing stay correct even if per-frame narration length varies
    a lot - no separate alignment/whisper step needed, since the duration
    is already known from the actual generated audio.

    Returns the .srt path, or None if there were no usable frames (so the
    caller can skip logging a path that doesn't exist).
    """
    lines: List[str] = []
    cursor = 0.0
    entry_num = 0

    for frame in storyboard.frames:
        duration = frame.duration or 0.0
        start = cursor
        end = cursor + duration
        cursor = end

        text = (frame.narration or "").strip()
        if not text or duration <= 0:
            # Skip b-roll/silent frames with no narration - nothing to caption
            continue

        entry_num += 1
        lines.append(str(entry_num))
        lines.append(f"{_format_srt_timestamp(start)} --> {_format_srt_timestamp(end)}")
        lines.append(text)
        lines.append("")  # blank separator line required by the SRT format

    if entry_num == 0:
        return None

    srt_path = str(Path(video_output_path).with_suffix(".srt"))
    Path(srt_path).write_text("\n".join(lines), encoding="utf-8")
    return srt_path




class StandardPipeline(LinearVideoPipeline):
    """
    Standard video generation pipeline
    
    Workflow:
    1. Generate/determine title
    2. Generate narrations (from topic or split fixed script)
    3. Generate image prompts for each narration
    4. For each frame:
       - Generate audio (TTS)
       - Generate image
       - Compose frame with template
       - Create video segment
    5. Concatenate all segments
    6. Add BGM (optional)
    
    Supports two modes:
    - "generate": LLM generates narrations from topic
    - "fixed": Use provided script as-is (each line = one narration)
    """
    
    # ==================== Lifecycle Methods ====================

    async def setup_environment(self, ctx: PipelineContext):
        """Step 1: Setup task directory and environment."""
        text = ctx.input_text
        mode = ctx.params.get("mode", "generate")
        
        logger.info(f"🚀 Starting StandardPipeline in '{mode}' mode")
        logger.info(f"   Text length: {len(text)} chars")
        
        # Create isolated task directory
        task_dir, task_id = create_task_output_dir()
        ctx.task_id = task_id
        ctx.task_dir = task_dir
        
        logger.info(f"📁 Task directory created: {task_dir}")
        logger.info(f"   Task ID: {task_id}")
        
        # Determine final video path
        output_path = ctx.params.get("output_path")
        if output_path is None:
            ctx.final_video_path = get_task_final_video_path(task_id)
        else:
            # We will copy to this path in finalize/post_production
            # For internal processing, we still use the task dir path? 
            # Actually StandardPipeline logic used get_task_final_video_path as the target for concat
            # and then copied. Let's stick to that.
            ctx.final_video_path = get_task_final_video_path(task_id)
            logger.info(f"   Will copy final video to: {output_path}")

    async def generate_content(self, ctx: PipelineContext):
        """Step 2: Generate or process script/narrations."""
        mode = ctx.params.get("mode", "generate")
        text = ctx.input_text
        n_scenes = ctx.params.get("n_scenes", 5)
        min_words = ctx.params.get("min_narration_words", 5)
        max_words = ctx.params.get("max_narration_words", 20)
        
        if mode == "generate":
            narrative_mode = ctx.params.get("narrative_mode", "standard")
            self._report_progress(ctx.progress_callback, "generating_narrations", 0.05)
            ctx.narrations = await generate_narrations_from_topic(
                self.llm,
                topic=text,
                n_scenes=n_scenes,
                min_words=min_words,
                max_words=max_words,
                narrative_mode=narrative_mode
            )
            logger.info(f"✅ Generated {len(ctx.narrations)} narrations (narrative_mode={narrative_mode})")
        else:  # fixed
            self._report_progress(ctx.progress_callback, "splitting_script", 0.05)
            split_mode = ctx.params.get("split_mode", "paragraph")
            ctx.narrations = await split_narration_script(text, split_mode=split_mode)
            logger.info(f"✅ Split script into {len(ctx.narrations)} segments (mode={split_mode})")
            logger.info(f"   Note: n_scenes={n_scenes} is ignored in fixed mode")

    async def determine_title(self, ctx: PipelineContext):
        """Step 3: Determine or generate video title."""
        # Note: Swapped order with generate_content in base class call, 
        # but in StandardPipeline original code, title was determined BEFORE narrations.
        # However, LinearVideoPipeline defines generate_content BEFORE determine_title.
        # This is fine as they are independent in StandardPipeline logic.
        
        title = ctx.params.get("title")
        mode = ctx.params.get("mode", "generate")
        text = ctx.input_text
        
        if title:
            ctx.title = title
            logger.info(f"   Title: '{title}' (user-specified)")
        else:
            self._report_progress(ctx.progress_callback, "generating_title", 0.01)
            if mode == "generate":
                ctx.title = await generate_title(self.llm, text, strategy="auto")
                logger.info(f"   Title: '{ctx.title}' (auto-generated)")
            else:  # fixed
                ctx.title = await generate_title(self.llm, text, strategy="llm")
                logger.info(f"   Title: '{ctx.title}' (LLM-generated)")

    async def plan_visuals(self, ctx: PipelineContext):
        """Step 4: Generate image prompts or visual descriptions."""
        # Detect template type to determine if media generation is needed
        frame_template = ctx.params.get("frame_template") or "1080x1920/default.html"
        
        template_name = Path(frame_template).name
        template_type = get_template_type(template_name)
        template_requires_media = (template_type in ["image", "video"])
        
        if template_type == "image":
            logger.info(f"📸 Template requires image generation")
        elif template_type == "video":
            logger.info(f"🎬 Template requires video generation")
        else:  # static
            logger.info(f"⚡ Static template - skipping media generation pipeline")
            logger.info(f"   💡 Benefits: Faster generation + Lower cost + No ComfyUI dependency")
        
        # Only generate image prompts if template requires media
        if template_requires_media:
            self._report_progress(ctx.progress_callback, "generating_image_prompts", 0.15)
            
            prompt_prefix = ctx.params.get("prompt_prefix")
            min_words = ctx.params.get("min_image_prompt_words", 25)
            max_words = ctx.params.get("max_image_prompt_words", 55)
            
            # Override prompt_prefix if provided
            original_prefix = None
            if prompt_prefix is not None:
                image_config = self.core.config.get("comfyui", {}).get("image", {})
                original_prefix = image_config.get("prompt_prefix")
                image_config["prompt_prefix"] = prompt_prefix
                logger.info(f"Using custom prompt_prefix: '{prompt_prefix}'")
            
            try:
                # Create progress callback wrapper for image prompt generation
                def image_prompt_progress(completed: int, total: int, message: str):
                    batch_progress = completed / total if total > 0 else 0
                    overall_progress = 0.15 + (batch_progress * 0.15)
                    self._report_progress(
                        ctx.progress_callback,
                        "generating_image_prompts",
                        overall_progress,
                        extra_info=message
                    )
                
                # Generate base image prompts
                base_image_prompts = await generate_image_prompts(
                    self.llm,
                    narrations=ctx.narrations,
                    min_words=min_words,
                    max_words=max_words,
                    progress_callback=image_prompt_progress
                )
                
                # Apply prompt prefix
                image_config = self.core.config.get("comfyui", {}).get("image", {})
                prompt_prefix_to_use = prompt_prefix if prompt_prefix is not None else image_config.get("prompt_prefix", "")
                
                ctx.image_prompts = []
                for base_prompt in base_image_prompts:
                    final_prompt = build_image_prompt(base_prompt, prompt_prefix_to_use)
                    ctx.image_prompts.append(final_prompt)
                
            finally:
                # Restore original prompt_prefix
                if original_prefix is not None:
                    image_config["prompt_prefix"] = original_prefix
            
            logger.info(f"✅ Generated {len(ctx.image_prompts)} image prompts")
        else:
            # Static template - skip image prompt generation entirely
            ctx.image_prompts = [None] * len(ctx.narrations)
            logger.info(f"⚡ Skipped image prompt generation (static template)")
            logger.info(f"   💡 Savings: {len(ctx.narrations)} LLM calls + {len(ctx.narrations)} media generations")

    async def initialize_storyboard(self, ctx: PipelineContext):
        """Step 5: Create Storyboard object and frames."""
        # === Handle TTS parameter compatibility ===
        tts_inference_mode = ctx.params.get("tts_inference_mode")
        tts_voice = ctx.params.get("tts_voice")
        voice_id = ctx.params.get("voice_id")
        tts_workflow = ctx.params.get("tts_workflow")
        
        final_voice_id = None
        final_tts_workflow = tts_workflow
        
        if tts_inference_mode:
            # New API from web UI
            if tts_inference_mode == "local":
                final_voice_id = tts_voice or "zh-CN-YunjianNeural"
                final_tts_workflow = None
                logger.debug(f"TTS Mode: local (voice={final_voice_id})")
            elif tts_inference_mode == "comfyui":
                final_voice_id = None
                logger.debug(f"TTS Mode: comfyui (workflow={final_tts_workflow})")
        else:
            # Old API
            final_voice_id = voice_id or tts_voice or "zh-CN-YunjianNeural"
            logger.debug(f"TTS Mode: legacy (voice_id={final_voice_id}, workflow={final_tts_workflow})")
            
        # Create config
        ctx.config = StoryboardConfig(
            task_id=ctx.task_id,
            n_storyboard=len(ctx.narrations), # Use actual length
            min_narration_words=ctx.params.get("min_narration_words", 5),
            max_narration_words=ctx.params.get("max_narration_words", 20),
            min_image_prompt_words=ctx.params.get("min_image_prompt_words", 25),
            max_image_prompt_words=ctx.params.get("max_image_prompt_words", 55),
            video_fps=ctx.params.get("video_fps", 30),
            tts_inference_mode=tts_inference_mode or "local",
            voice_id=final_voice_id,
            tts_workflow=final_tts_workflow,
            tts_speed=ctx.params.get("tts_speed", 1.2),
            ref_audio=ctx.params.get("ref_audio"),
            media_width=ctx.params.get("media_width"),
            media_height=ctx.params.get("media_height"),
            media_workflow=ctx.params.get("media_workflow"),
            api_video_params=ctx.params.get("api_video_params"),
            frame_template=ctx.params.get("frame_template") or "1080x1920/default.html",
            template_params=ctx.params.get("template_params")
        )
        
        # Create storyboard
        ctx.storyboard = Storyboard(
            title=ctx.title,
            config=ctx.config,
            content_metadata=ctx.params.get("content_metadata"),
            created_at=datetime.now()
        )
        
        # Create frames
        for i, (narration, image_prompt) in enumerate(zip(ctx.narrations, ctx.image_prompts)):
            frame = StoryboardFrame(
                index=i,
                narration=narration,
                image_prompt=image_prompt,
                created_at=datetime.now()
            )
            ctx.storyboard.frames.append(frame)
        
        # Persist an early checkpoint (status="running") right away, before any
        # frame is generated. This makes the task resumable/discoverable even
        # if the process crashes or disconnects on the very first frame.
        try:
            await self.core.persistence.save_task_metadata(ctx.task_id, {
                "task_id": ctx.task_id,
                "created_at": ctx.storyboard.created_at.isoformat(),
                "status": "running",
                "input": {**ctx.params, "text": ctx.input_text, "title": ctx.title},
            })
            await self.core.persistence.save_storyboard(ctx.task_id, ctx.storyboard)
        except Exception as e:
            logger.warning(f"⚠️ Failed to save initial checkpoint: {e}")

    async def resume_until_review(
        self,
        task_id: str,
        progress_callback: Optional[Callable[[ProgressEvent], None]] = None
    ) -> PipelineContext:
        """
        Resume an interrupted/incomplete task: reload its storyboard checkpoint
        from disk and finish producing whatever frames don't have a
        video_segment_path yet (already-done frames are skipped automatically
        by produce_assets). Returns a PipelineContext ready for review, same
        as generate_until_review().
        """
        storyboard = await self.core.persistence.load_storyboard(task_id)
        if storyboard is None:
            raise ValueError(f"No storyboard checkpoint found for task '{task_id}'")

        ctx = PipelineContext(
            input_text="",
            params={},
            progress_callback=progress_callback,
            task_id=task_id,
            task_dir=str(self.core.persistence.get_task_dir(task_id)),
            title=storyboard.title,
            config=storyboard.config,
            storyboard=storyboard,
        )
        ctx.final_video_path = get_task_final_video_path(task_id)

        logger.info(f"▶️ Resuming task {task_id}: "
                    f"{sum(1 for f in storyboard.frames if f.video_segment_path)}/"
                    f"{len(storyboard.frames)} frames already done")

        await self.produce_assets(ctx)
        return ctx

    async def handle_exception(self, ctx: PipelineContext, error: Exception):
        """Mark the task as failed (as opposed to a silent process crash/
        disconnect, which leaves the last-saved status as 'running' - both
        are treated as resumable, but this gives a more accurate status)."""
        await super().handle_exception(ctx, error)
        if ctx.task_id:
            try:
                await self.core.persistence.update_task_status(
                    ctx.task_id, "failed", error=str(error)
                )
            except Exception as e:
                logger.warning(f"⚠️ Failed to update task status to 'failed': {e}")

    async def produce_assets(self, ctx: PipelineContext):
        """Step 6: Generate audio, images, and render frames (Core processing)."""
        storyboard = ctx.storyboard
        config = ctx.config
        
        # Guards concurrent writes to the same storyboard checkpoint file when
        # frames are processed in parallel (RunningHub branch below).
        checkpoint_lock = asyncio.Lock()
        
        async def save_checkpoint():
            """Persist current storyboard state so completed frames survive a
            crash/disconnect. Best-effort: a failure here must never abort
            asset production."""
            if not ctx.task_id:
                return
            try:
                async with checkpoint_lock:
                    await self.core.persistence.save_storyboard(ctx.task_id, storyboard)
            except Exception as e:
                logger.warning(f"⚠️ Failed to save checkpoint after frame: {e}")
        
        # Check if using RunningHub workflows for parallel processing
        is_runninghub = (
            (config.tts_workflow and config.tts_workflow.startswith("runninghub/")) or
            (config.media_workflow and config.media_workflow.startswith("runninghub/"))
        )
        
        # Get concurrent limit from config_manager (supports hot reload without restart)
        from pixelle_video.config import config_manager
        runninghub_concurrent_limit = config_manager.config.comfyui.runninghub_concurrent_limit or 1
        
        if is_runninghub and runninghub_concurrent_limit > 1:
            logger.info(f"🚀 Using parallel processing for RunningHub workflows (max {runninghub_concurrent_limit} concurrent)")
            
            semaphore = asyncio.Semaphore(runninghub_concurrent_limit)
            completed_count = 0
            
            async def process_frame_with_semaphore(i: int, frame: StoryboardFrame):
                nonlocal completed_count
                if frame.video_segment_path:
                    # Already fully processed (e.g. resuming an interrupted run) - skip.
                    logger.info(f"⏭️ Frame {i+1} already done, skipping")
                    completed_count += 1
                    return i, frame
                async with semaphore:
                    base_progress = 0.2
                    frame_range = 0.6
                    per_frame_progress = frame_range / len(storyboard.frames)
                    
                    # Create frame-specific progress callback
                    def frame_progress_callback(event: ProgressEvent):
                        overall_progress = base_progress + (per_frame_progress * completed_count) + (per_frame_progress * event.progress)
                        if ctx.progress_callback:
                            adjusted_event = ProgressEvent(
                                event_type=event.event_type,
                                progress=overall_progress,
                                frame_current=i+1,
                                frame_total=len(storyboard.frames),
                                step=event.step,
                                action=event.action
                            )
                            ctx.progress_callback(adjusted_event)
                    
                    # Report frame start
                    self._report_progress(
                        ctx.progress_callback,
                        "processing_frame",
                        base_progress + (per_frame_progress * completed_count),
                        frame_current=i+1,
                        frame_total=len(storyboard.frames)
                    )
                    
                    processed_frame = await self.core.frame_processor(
                        frame=frame,
                        storyboard=storyboard,
                        config=config,
                        total_frames=len(storyboard.frames),
                        progress_callback=frame_progress_callback
                    )
                    
                    completed_count += 1
                    logger.info(f"✅ Frame {i+1} completed ({processed_frame.duration:.2f}s) [{completed_count}/{len(storyboard.frames)}]")
                    
                    # Write the frame into the storyboard and checkpoint immediately,
                    # instead of waiting for every parallel task to finish.
                    storyboard.frames[i] = processed_frame
                    await save_checkpoint()
                    
                    return i, processed_frame
            
            # Create all tasks and execute in parallel
            tasks = [process_frame_with_semaphore(i, frame) for i, frame in enumerate(storyboard.frames)]
            results = await asyncio.gather(*tasks)
            
            # Frames were already written into storyboard.frames above as each
            # completed. Total duration is recomputed once at the end of this
            # method (safe for both fresh runs and resumed/skipped frames).
            logger.info("✅ All frames processed in parallel")
        else:
            # Serial processing for non-RunningHub workflows
            logger.info("⚙️ Using serial processing (non-RunningHub workflow)")
            
            for i, frame in enumerate(storyboard.frames):
                if frame.video_segment_path:
                    # Already fully processed (e.g. resuming an interrupted run) - skip.
                    logger.info(f"⏭️ Frame {i+1} already done, skipping")
                    continue
                
                base_progress = 0.2
                frame_range = 0.6
                per_frame_progress = frame_range / len(storyboard.frames)
                
                # Create frame-specific progress callback
                def frame_progress_callback(event: ProgressEvent):
                    overall_progress = base_progress + (per_frame_progress * i) + (per_frame_progress * event.progress)
                    if ctx.progress_callback:
                        adjusted_event = ProgressEvent(
                            event_type=event.event_type,
                            progress=overall_progress,
                            frame_current=event.frame_current,
                            frame_total=event.frame_total,
                            step=event.step,
                            action=event.action
                        )
                        ctx.progress_callback(adjusted_event)
                
                # Report frame start
                self._report_progress(
                    ctx.progress_callback,
                    "processing_frame",
                    base_progress + (per_frame_progress * i),
                    frame_current=i+1,
                    frame_total=len(storyboard.frames)
                )
                
                processed_frame = await self.core.frame_processor(
                    frame=frame,
                    storyboard=storyboard,
                    config=config,
                    total_frames=len(storyboard.frames),
                    progress_callback=frame_progress_callback
                )
                logger.info(f"✅ Frame {i+1} completed ({processed_frame.duration:.2f}s)")
                
                # Checkpoint right away so scenes 1..i survive a crash/disconnect
                # even if frame i+1 fails or the process dies mid-way.
                await save_checkpoint()
                
                # Periodic GPU rest for long runs (e.g. 300-400 scenes) - lets
                # the GPU cool down instead of running at full load for many
                # hours straight. Configured via rest_every_n/rest_seconds in
                # ctx.params; disabled (0) by default for normal short videos.
                rest_every_n = ctx.params.get("rest_every_n", 0)
                rest_seconds = ctx.params.get("rest_seconds", 0)
                is_last_frame = (i == len(storyboard.frames) - 1)
                if rest_every_n and rest_seconds and not is_last_frame and (i + 1) % rest_every_n == 0:
                    logger.info(f"🌡️ Resting {rest_seconds}s after frame {i+1} to let GPU cool down...")
                    self._report_progress(
                        ctx.progress_callback,
                        "resting",
                        base_progress + (per_frame_progress * (i + 1)),
                        frame_current=i+1,
                        frame_total=len(storyboard.frames)
                    )
                    await asyncio.sleep(rest_seconds)
        
        # Recompute total duration once, from scratch, so resumed runs (where
        # some frames are skipped because they're already done) never double-count.
        storyboard.total_duration = sum(f.duration for f in storyboard.frames)

    async def post_production(self, ctx: PipelineContext):
        """Step 7: Concatenate videos and add BGM."""
        self._report_progress(ctx.progress_callback, "concatenating", 0.85)
        
        storyboard = ctx.storyboard
        segment_paths = [frame.video_segment_path for frame in storyboard.frames]
        
        video_service = VideoService()
        
        final_video_path = video_service.concat_videos(
            videos=segment_paths,
            output=ctx.final_video_path,
            bgm_path=ctx.params.get("bgm_path"),
            bgm_volume=ctx.params.get("bgm_volume", 0.2),
            bgm_mode=ctx.params.get("bgm_mode", "loop")
        )
        
        storyboard.final_video_path = final_video_path
        storyboard.completed_at = datetime.now()
        
        # Copy to user-specified path if provided
        user_specified_output = ctx.params.get("output_path")
        if user_specified_output:
            Path(user_specified_output).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(final_video_path, user_specified_output)
            logger.info(f"📹 Final video copied to: {user_specified_output}")
            ctx.final_video_path = user_specified_output
            storyboard.final_video_path = user_specified_output
        
        logger.success(f"🎬 Video generation completed: {ctx.final_video_path}")

        # Export a standalone .srt subtitle file (one entry per frame, timed
        # using each frame's real audio/video duration) so captions can be
        # uploaded to YouTube separately and toggled by viewers, instead of
        # being burned into the video image itself.
        srt_path = _write_srt_file(storyboard, ctx.final_video_path)
        if srt_path:
            logger.success(f"📝 Subtitle file generated: {srt_path}")
        else:
            logger.debug("No narration frames to caption - skipped .srt export")

    async def finalize(self, ctx: PipelineContext) -> VideoGenerationResult:
        """Step 8: Create result object and persist metadata."""
        self._report_progress(ctx.progress_callback, "completed", 1.0)
        
        video_path_obj = Path(ctx.final_video_path)
        file_size = video_path_obj.stat().st_size
        
        result = VideoGenerationResult(
            video_path=ctx.final_video_path,
            storyboard=ctx.storyboard,
            duration=ctx.storyboard.total_duration,
            file_size=file_size
        )
        
        ctx.result = result
        
        logger.info(f"✅ Generated video: {ctx.final_video_path}")
        logger.info(f"   Duration: {ctx.storyboard.total_duration:.2f}s")
        logger.info(f"   Size: {file_size / (1024*1024):.2f} MB")
        logger.info(f"   Frames: {len(ctx.storyboard.frames)}")
        
        # Persist metadata
        await self._persist_task_data(ctx)
        
        return result

    async def _persist_task_data(self, ctx: PipelineContext):
        """
        Persist task metadata and storyboard to filesystem
        """
        try:
            storyboard = ctx.storyboard
            result = ctx.result
            task_id = storyboard.config.task_id
            
            if not task_id:
                logger.warning("No task_id in storyboard, skipping persistence")
                return
            
            # Build metadata
            input_with_title = ctx.params.copy()
            input_with_title["text"] = ctx.input_text # Ensure text is included
            if not input_with_title.get("title"):
                input_with_title["title"] = storyboard.title
            
            metadata = {
                "task_id": task_id,
                "created_at": storyboard.created_at.isoformat() if storyboard.created_at else None,
                "completed_at": storyboard.completed_at.isoformat() if storyboard.completed_at else None,
                "status": "completed",
                
                "input": input_with_title,
                
                "result": {
                    "video_path": result.video_path,
                    "duration": result.duration,
                    "file_size": result.file_size,
                    "n_frames": len(storyboard.frames)
                },
                
                "config": {
                    "llm_model": self.core.config.get("llm", {}).get("model", "unknown"),
                    "llm_base_url": self.core.config.get("llm", {}).get("base_url", "unknown"),
                    "comfyui_url": self.core.config.get("comfyui", {}).get("comfyui_url", "unknown"),
                    "runninghub_enabled": bool(self.core.config.get("comfyui", {}).get("runninghub_api_key")),
                }
            }
            
            # Save metadata
            await self.core.persistence.save_task_metadata(task_id, metadata)
            logger.info(f"💾 Saved task metadata: {task_id}")
            
            # Save storyboard
            await self.core.persistence.save_storyboard(task_id, storyboard)
            logger.info(f"💾 Saved storyboard: {task_id}")
            
        except Exception as e:
            logger.error(f"Failed to persist task data: {e}")
            # Don't raise - persistence failure shouldn't break video generation
