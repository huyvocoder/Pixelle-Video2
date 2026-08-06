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
Output preview components for web UI (right column)
"""

import base64
import os
from pathlib import Path

import streamlit as st
from loguru import logger

from web.i18n import tr, get_language
from web.utils.async_helpers import run_async
from pixelle_video.models.progress import ProgressEvent
from pixelle_video.pipelines.linear import PipelineContext
from pixelle_video.config import config_manager
from web.utils.persist_inputs import save_last_inputs
from web.components.scene_review import render_scene_review, render_last_result_if_any


def _find_resumable_task(pixelle_video, exclude_ids: set):
    """
    Find the most recent task that looks interrupted (status running/failed,
    not in the dismissed set), and how many of its frames are already done.
    Returns (task_id, title, n_done, n_total) or None.
    """
    try:
        tasks = run_async(pixelle_video.persistence.list_tasks(limit=10))
    except Exception as e:
        logger.warning(f"Failed to list tasks for resume check: {e}")
        return None

    for task in tasks:
        task_id = task.get("task_id")
        status = task.get("status")
        if not task_id or task_id in exclude_ids:
            continue
        if status not in ("running", "failed"):
            continue
        try:
            storyboard = run_async(pixelle_video.persistence.load_storyboard(task_id))
        except Exception:
            continue
        if not storyboard or not storyboard.frames:
            continue
        n_total = len(storyboard.frames)
        n_done = sum(1 for f in storyboard.frames if f.video_segment_path)
        if n_done >= n_total:
            # Somehow all frames done but status never flipped to completed -
            # not worth surfacing as "resumable", let it be handled normally.
            continue
        return task_id, storyboard.title, n_done, n_total
    return None


def render_output_preview(pixelle_video, video_params):
    """Render output preview section (right column)"""
    # Check if batch mode
    is_batch = video_params.get("batch_mode", False)
    
    if is_batch:
        # Batch generation mode
        render_batch_output(pixelle_video, video_params)
    else:
        # Single video generation mode (original logic)
        render_single_output(pixelle_video, video_params)


def render_single_output(pixelle_video, video_params):
    """Render single video generation output"""
    # Capture the pipeline name now, before the local `video_params` name
    # below gets reassigned to a fresh dict without a "pipeline" key.
    # NOTE: video_params["pipeline"] is the UI-level pipeline id (e.g. "quick_create",
    # set in web/pipelines/standard.py's StandardPipelineUI.name) - it is NOT the
    # same namespace as pixelle_video.pipelines' keys ("standard", "custom",
    # "asset_based"), which live in pixelle_video/service.py. This component
    # (output_preview.py) is only ever rendered from the Quick Create UI tab,
    # which always corresponds to the backend "standard" pipeline.
    pipeline_name = "standard"

    # Extract parameters from video_params dict
    text = video_params.get("text", "")
    mode = video_params.get("mode", "generate")
    title = video_params.get("title")
    n_scenes = video_params.get("n_scenes", 5)
    split_mode = video_params.get("split_mode", "paragraph")
    bgm_path = video_params.get("bgm_path")
    bgm_volume = video_params.get("bgm_volume", 0.2)
    
    tts_mode = video_params.get("tts_inference_mode", "local")
    selected_voice = video_params.get("tts_voice")
    tts_speed = video_params.get("tts_speed")
    tts_workflow_key = video_params.get("tts_workflow")
    ref_audio_path = video_params.get("ref_audio")
    
    frame_template = video_params.get("frame_template")
    custom_values_for_video = video_params.get("template_params", {})
    workflow_key = video_params.get("media_workflow")
    api_video_params = video_params.get("api_video_params")
    prompt_prefix = video_params.get("prompt_prefix", "")
    rest_every_n = video_params.get("rest_every_n", 0)
    rest_seconds = video_params.get("rest_seconds", 0)
    
    with st.container(border=False):
        st.markdown(f"**{tr('section.video_generation')}**")
        
        # Check if system is configured
        if not config_manager.validate():
            st.warning(tr("settings.not_configured"))
        
        # If a review is currently in progress (frames generated, not yet composed),
        # show the review grid instead of the Generate button.
        if st.session_state.get("review_active"):
            render_scene_review(pixelle_video, pipeline_name)
            return
        
        # Show the final composed video from the last completed review, if any.
        render_last_result_if_any()
        
        # ====================================================================
        # Resumable task detection: a previous video was still being
        # generated (scenes 1..k done) when the app/browser was interrupted.
        # Offer to continue it, or explicitly discard it and start fresh.
        # ====================================================================
        dismissed_ids = st.session_state.setdefault("dismissed_resume_task_ids", set())
        resumable = _find_resumable_task(pixelle_video, dismissed_ids)

        if resumable:
            resume_task_id, resume_title, n_done, n_total = resumable
            with st.container(border=False):
                st.warning(
                    f"⚠️ Có 1 video đang gen dở: **{resume_title or resume_task_id}** "
                    f"({n_done}/{n_total} cảnh đã xong)."
                )

                if st.session_state.get("confirm_discard_resume") == resume_task_id:
                    st.error("Bỏ video đang gen dở này? Các cảnh đã gen sẽ không dùng được nữa trừ khi bạn Tiếp tục sau.")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Xác nhận bỏ", use_container_width=True, key="confirm_discard_yes"):
                            try:
                                run_async(pixelle_video.persistence.update_task_status(resume_task_id, "cancelled"))
                            except Exception as e:
                                logger.warning(f"Failed to mark task {resume_task_id} as cancelled: {e}")
                            dismissed_ids.add(resume_task_id)
                            st.session_state.pop("confirm_discard_resume", None)
                            st.rerun()
                    with c2:
                        if st.button("↩️ Thôi, quay lại", use_container_width=True, key="confirm_discard_no"):
                            st.session_state.pop("confirm_discard_resume", None)
                            st.rerun()
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("▶️ Tiếp tục video này", type="primary", use_container_width=True, key="resume_btn"):
                            pipeline_instance = pixelle_video.pipelines[pipeline_name]
                            with st.spinner(f"Đang tiếp tục từ cảnh {n_done + 1}..."):
                                try:
                                    ctx = run_async(pipeline_instance.resume_until_review(resume_task_id))
                                except Exception as e:
                                    st.error(f"Không thể tiếp tục task này: {e}")
                                    logger.exception(e)
                                    st.stop()
                            st.session_state["review_active"] = True
                            st.session_state["review_ctx"] = ctx
                            st.session_state["review_selected_frame"] = 0
                            st.rerun()
                    with c2:
                        if st.button("🗑️ Bỏ, gen video mới", use_container_width=True, key="discard_btn"):
                            st.session_state["confirm_discard_resume"] = resume_task_id
                            st.rerun()
            # While an unresolved resumable task exists, don't show the normal
            # Generate button yet - force the user to pick Continue or Discard.
            return
        
        # Generate Button
        if st.button(tr("btn.generate"), type="primary", use_container_width=True):
            # Persist current form values so they're pre-filled next time
            # (regardless of whether generation below succeeds or fails).
            # video_params already contains everything from content_input +
            # bgm + style_config (TTS mode/voice/speed, workflow, template, prefix...).
            save_last_inputs(video_params)

            # Validate system configuration
            if not config_manager.validate():
                st.error(tr("settings.not_configured"))
                st.stop()
            
            # Validate input
            if not text:
                st.error(tr("error.input_required"))
                st.stop()

            from pixelle_video.utils.template_util import get_template_type
            if frame_template and get_template_type(frame_template) == "video" and not workflow_key:
                st.error(
                    "请选择视频生成工作流或 API 视频模型后再生成。"
                    if get_language() == "zh_CN"
                    else "Please select a video workflow or API video model before generating."
                )
                st.stop()
            
            # Show progress
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Record start time for generation
            import time
            start_time = time.time()
            
            try:
                # Per-scene grid placeholders. Populated page-by-page (same
                # PAGE_SIZE as the post-generation review grid) instead of all
                # at once - for a 400-scene video, building 400 st.empty()
                # cells + redrawing all of them up front is expensive for no
                # benefit, since only ~1 cell changes per progress event.
                # Only the page containing the scene currently being
                # processed is ever mounted; older/later pages aren't shown
                # here (the full grid with regen is available afterwards in
                # scene review, which already paginates).
                GRID_PAGE_SIZE = 30
                frame_placeholders = {}
                grid_area = st.empty()
                grid_state = {"page_idx": -1, "start": 0, "end": 0, "n_frames": 0}
                
                def render_frame_cell(idx: int, frame, step_label: str = None):
                    """(Re)draw a single scene's cell based on its current state."""
                    ph = frame_placeholders.get(idx)
                    if ph is None:
                        return
                    thumb = (frame.composed_image_path or frame.image_path) if frame is not None else None
                    if thumb and os.path.exists(thumb):
                        # Show the image as soon as it exists - don't wait for
                        # the whole frame (audio+segment) to finish too.
                        is_fully_done = bool(frame.video_segment_path)
                        with ph.container():
                            st.image(thumb, use_container_width=True)
                            st.caption(f"✅ Cảnh {idx + 1}" if is_fully_done else f"🖼️ Cảnh {idx + 1} - đang hoàn tất...")
                    else:
                        label = step_label or "đang chờ"
                        ph.markdown(
                            f"""
                            <div style="
                                border: 1px solid rgba(250,250,250,0.12);
                                border-radius: 12px;
                                aspect-ratio: 16/9;
                                display: flex;
                                flex-direction: column;
                                align-items: center;
                                justify-content: center;
                                gap: 0.3rem;
                                background: rgba(250,250,250,0.03);
                                color: rgba(250,250,250,0.75);
                                text-align: center;
                                padding: 0.5rem;
                            ">
                                <div style="font-weight:600;">⏳ Cảnh {idx + 1}</div>
                                <div style="font-size:0.82rem; opacity:0.8;">{label}...</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                
                def build_grid_page(page_idx: int):
                    """(Re)mount only one page's worth of cells (<=GRID_PAGE_SIZE)
                    into grid_area, replacing whatever page was shown before."""
                    n_frames = grid_state["n_frames"]
                    n_pages = max(1, (n_frames + GRID_PAGE_SIZE - 1) // GRID_PAGE_SIZE)
                    page_idx = max(0, min(page_idx, n_pages - 1))
                    start = page_idx * GRID_PAGE_SIZE
                    end = min(start + GRID_PAGE_SIZE, n_frames)

                    frame_placeholders.clear()
                    n_cols = 3
                    with grid_area.container():
                        st.caption(
                            f"🎬 {n_frames} cảnh - đang xử lý (trang {page_idx + 1}/{n_pages}, "
                            f"cảnh {start + 1}-{end}):"
                        )
                        grid_cols = st.columns(n_cols)
                        for i in range(start, end):
                            with grid_cols[(i - start) % n_cols]:
                                frame_placeholders[i] = st.empty()
                                render_frame_cell(i, ctx.storyboard.frames[i])

                    grid_state["page_idx"] = page_idx
                    grid_state["start"] = start
                    grid_state["end"] = end

                # Progress callback: always drives the overall bar/status text;
                # once the grid has been built, also drives the matching cell,
                # switching pages automatically as generation moves past the
                # current page's range.
                def update_progress(event: ProgressEvent):
                    """Update progress bar and status text from ProgressEvent"""
                    if event.event_type == "frame_step":
                        action_key = f"progress.step_{event.action}"
                        action_text = tr(action_key)
                        message = tr(
                            "progress.frame_step",
                            current=event.frame_current,
                            total=event.frame_total,
                            step=event.step,
                            action=action_text
                        )
                    elif event.event_type == "processing_frame":
                        message = tr(
                            "progress.frame",
                            current=event.frame_current,
                            total=event.frame_total
                        )
                    else:
                        message = tr(f"progress.{event.event_type}")
                    
                    if event.extra_info:
                        message = f"{message} - {event.extra_info}"
                    
                    status_text.text(message)
                    progress_bar.progress(min(int(event.progress * 100), 99))
                    
                    # Live-update the corresponding scene cell, if the grid
                    # has been built yet (it hasn't during the script/planning
                    # phase, only from produce_assets onward). Jump to the
                    # right page first if the current scene moved past it.
                    if event.frame_current and grid_state["n_frames"]:
                        idx = event.frame_current - 1
                        if not (grid_state["start"] <= idx < grid_state["end"]):
                            build_grid_page(idx // GRID_PAGE_SIZE)
                        frame = ctx.storyboard.frames[idx] if ctx and ctx.storyboard else None
                        step_label = tr(f"progress.step_{event.action}") if event.event_type == "frame_step" else None
                        render_frame_cell(idx, frame, step_label)
                
                # Generate video (directly pass parameters)
                # Note: media_width and media_height are auto-determined from template
                video_params = {
                    "text": text,
                    "mode": mode,
                    "title": title if title else None,
                    "n_scenes": n_scenes,
                    "split_mode": split_mode,
                    "media_workflow": workflow_key,
                    "api_video_params": api_video_params,
                    "frame_template": frame_template,
                    "prompt_prefix": prompt_prefix,
                    "bgm_path": bgm_path,
                    "bgm_volume": bgm_volume if bgm_path else 0.2,
                    "rest_every_n": rest_every_n,
                    "rest_seconds": rest_seconds,
                    "progress_callback": update_progress,
                    "media_width": st.session_state.get('template_media_width'),
                    "media_height": st.session_state.get('template_media_height'),
                }
                # Add TTS parameters based on mode
                video_params["tts_inference_mode"] = tts_mode
                if tts_mode == "local":
                    video_params["tts_voice"] = selected_voice
                    video_params["tts_speed"] = tts_speed
                else:  # comfyui
                    video_params["tts_workflow"] = tts_workflow_key
                    if ref_audio_path:
                        video_params["ref_audio"] = str(ref_audio_path)
                
                # Add custom template parameters if any
                if custom_values_for_video:
                    video_params["template_params"] = custom_values_for_video
                
                pipeline_instance = pixelle_video.pipelines[pipeline_name]
                
                # ============================================================
                # Phase A: run everything up through initialize_storyboard.
                # This is fast (LLM calls only, no media generation) and gives
                # us ctx.storyboard.frames (count + narration/image_prompt per
                # frame) with nothing generated yet - exactly what we need to
                # draw the grid of "waiting" cells before any real work starts.
                # ============================================================
                text_arg = video_params.pop("text")
                progress_cb_arg = video_params.pop("progress_callback")
                ctx = PipelineContext(
                    input_text=text_arg,
                    params=video_params,
                    progress_callback=progress_cb_arg
                )
                
                async def _run_planning_phase():
                    await pipeline_instance.setup_environment(ctx)
                    await pipeline_instance.generate_content(ctx)
                    await pipeline_instance.determine_title(ctx)
                    await pipeline_instance.plan_visuals(ctx)
                    await pipeline_instance.initialize_storyboard(ctx)
                
                run_async(_run_planning_phase())
                
                # ============================================================
                # Build the live grid now that we know how many scenes there are.
                # Only page 1 is mounted up front; update_progress() switches
                # pages automatically as generation advances past 30 scenes.
                # ============================================================
                n_frames = len(ctx.storyboard.frames)
                st.markdown("---")
                grid_state["n_frames"] = n_frames
                build_grid_page(0)
                
                # ============================================================
                # Phase B: actually produce all assets. update_progress (still
                # wired to ctx.progress_callback) now updates the grid live as
                # each scene's steps complete, thanks to frame_placeholders
                # being populated above.
                # ============================================================
                run_async(pipeline_instance.produce_assets(ctx))
                
                # Final pass: make sure the currently-mounted page's cells
                # reflect their true final state (in case the last event for
                # a scene fired just before its video_segment_path was
                # actually set). Only the page still on screen is touched -
                # earlier pages already reached their final "done" state
                # since generation never revisits a scene once it moves on.
                for i in range(grid_state["start"], grid_state["end"]):
                    render_frame_cell(i, ctx.storyboard.frames[i])
                
                progress_bar.progress(100)
                status_text.text(tr("status.success"))
                
                st.session_state["review_active"] = True
                st.session_state["review_ctx"] = ctx
                st.session_state["review_selected_frame"] = 0
                st.session_state.pop("last_composed_result", None)
                st.rerun()
                
            except Exception as e:
                status_text.text("")
                progress_bar.empty()
                st.error(tr("status.error", error=str(e)))
                logger.exception(e)
                st.stop()


def render_batch_output(pixelle_video, video_params):
    """Render batch generation output (minimal, redirect to History)"""
    topics = video_params.get("topics", [])
    
    with st.container(border=False):
        st.markdown(f"**{tr('batch.section_generation')}**")
        
        # Check if topics are provided
        if not topics:
            st.warning(tr("batch.no_topics"))
            return
        
        # Check system configuration
        if not config_manager.validate():
            st.warning(tr("settings.not_configured"))
            return
        
        batch_count = len(topics)
        
        # Display batch info
        st.info(tr("batch.prepare_info", count=batch_count))
        
        # Estimated time (optional)
        estimated_minutes = batch_count * 3  # Assume 3 minutes per video
        st.caption(tr("batch.estimated_time", minutes=estimated_minutes))
        
        # Generate button with batch semantics
        if st.button(
            tr("batch.generate_button", count=batch_count),
            type="primary",
            use_container_width=True,
            help=tr("batch.generate_help")
        ):
            # Prepare shared config
            shared_config = {
                "title_prefix": video_params.get("title_prefix"),
                "n_scenes": video_params.get("n_scenes") or 5,
                "media_workflow": video_params.get("media_workflow"),
                "api_video_params": video_params.get("api_video_params"),
                "frame_template": video_params.get("frame_template"),
                "prompt_prefix": video_params.get("prompt_prefix") or "",
                "bgm_path": video_params.get("bgm_path"),
                "bgm_volume": video_params.get("bgm_volume") or 0.2,
                "tts_inference_mode": video_params.get("tts_inference_mode") or "local",
                "media_width": video_params.get("media_width"),
                "media_height": video_params.get("media_height"),
            }
            # Add TTS parameters based on mode (only add non-None values)
            if shared_config["tts_inference_mode"] == "local":
                tts_voice = video_params.get("tts_voice")
                tts_speed = video_params.get("tts_speed")
                if tts_voice:
                    shared_config["tts_voice"] = tts_voice
                if tts_speed:
                    shared_config["tts_speed"] = tts_speed
            else:  # comfyui
                tts_workflow = video_params.get("tts_workflow")
                if tts_workflow:
                    shared_config["tts_workflow"] = tts_workflow
                ref_audio = video_params.get("ref_audio")
                if ref_audio:
                    shared_config["ref_audio"] = str(ref_audio)
            
            # Add template parameters
            if video_params.get("template_params"):
                shared_config["template_params"] = video_params["template_params"]
            
            # UI containers
            overall_progress_container = st.container()
            current_task_container = st.container()
            
            # Overall progress UI
            overall_progress_bar = overall_progress_container.progress(0)
            overall_status = overall_progress_container.empty()
            
            # Current task progress UI
            current_task_title = current_task_container.empty()
            current_task_progress = current_task_container.progress(0)
            current_task_status = current_task_container.empty()
            
            # Overall progress callback
            def update_overall_progress(current, total, topic):
                progress = (current - 1) / total
                overall_progress_bar.progress(progress)
                overall_status.markdown(
                    f"📊 **{tr('batch.overall_progress')}**: {current}/{total} ({int(progress * 100)}%)"
                )
            
            # Single task progress callback factory
            def make_task_progress_callback(task_idx, topic):
                def callback(event: ProgressEvent):
                    # Display current task title
                    current_task_title.markdown(f"🎬 **{tr('batch.current_task')} {task_idx}**: {topic}")
                    
                    # Update task detailed progress
                    if event.event_type == "frame_step":
                        action_key = f"progress.step_{event.action}"
                        action_text = tr(action_key)
                        message = tr(
                            "progress.frame_step",
                            current=event.frame_current,
                            total=event.frame_total,
                            step=event.step,
                            action=action_text
                        )
                    elif event.event_type == "processing_frame":
                        message = tr(
                            "progress.frame",
                            current=event.frame_current,
                            total=event.frame_total
                        )
                    else:
                        message = tr(f"progress.{event.event_type}")
                    
                    current_task_progress.progress(event.progress)
                    current_task_status.text(message)
                
                return callback
            
            # Execute batch generation
            from web.utils.batch_manager import SimpleBatchManager
            import time
            
            batch_manager = SimpleBatchManager()
            start_time = time.time()
            
            batch_result = batch_manager.execute_batch(
                pixelle_video=pixelle_video,
                topics=topics,
                shared_config=shared_config,
                overall_progress_callback=update_overall_progress,
                task_progress_callback_factory=make_task_progress_callback
            )
            
            total_time = time.time() - start_time
            
            # Clear progress displays
            overall_progress_bar.progress(1.0)
            overall_status.markdown(f"✅ **{tr('batch.completed')}**")
            current_task_title.empty()
            current_task_progress.empty()
            current_task_status.empty()
            
            # Display results summary
            st.markdown("---")
            st.markdown(f"**{tr('batch.results_title')}**")
            
            col1, col2, col3 = st.columns(3)
            col1.metric(tr("batch.total"), batch_result["total_count"])
            col2.metric(f"✅ {tr('batch.success')}", batch_result["success_count"])
            col3.metric(f"❌ {tr('batch.failed')}", batch_result["failed_count"])
            
            # Display total time
            minutes = int(total_time / 60)
            seconds = int(total_time % 60)
            st.caption(f"⏱️ {tr('batch.total_time')}: {minutes}{tr('batch.minutes')}{seconds}{tr('batch.seconds')}")
            
            # Redirect to History page
            st.markdown("---")
            st.success(tr("batch.success_message"))
            st.info(tr("batch.view_in_history"))
            
            # Button to go to History page using JavaScript URL navigation
            st.markdown(
                f"""
                <a href="/History" target="_blank">
                    <button style="
                        width: 100%;
                        padding: 0.5rem 1rem;
                        background-color: white;
                        color: rgb(49, 51, 63);
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        border-radius: 0.5rem;
                        cursor: pointer;
                        font-size: 1rem;
                        font-weight: 400;
                        text-align: center;
                    ">
                        📚 {tr('batch.goto_history')}
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )
            
            # Show failed tasks if any
            if batch_result["errors"]:
                st.markdown("---")
                st.markdown(f"#### {tr('batch.failed_list')}")
                
                for item in batch_result["errors"]:
                    with st.expander(f"🔴 {tr('batch.task')} {item['index']}: {item['topic']}", expanded=False):
                        st.error(f"**{tr('batch.error')}**: {item['error']}")
                        
                        # Detailed error (collapsed)
                        with st.expander(tr("batch.error_detail")):
                            st.code(item['traceback'], language="python")
    
