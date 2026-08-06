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
Scene Review UI

Shown after generate_until_review() finishes (all frames produced) and
before compose_and_finalize() is called. Lets the user:
- See every scene's image in a grid
- Zoom into any scene (with prev/next navigation, no need to close/reopen)
- Regenerate a single scene's image (voice is kept as-is)
- Only compose the final video once they're happy with everything
"""

import base64
import os

import streamlit as st
from loguru import logger

from web.i18n import tr, get_language
from web.utils.async_helpers import run_async
from pixelle_video.services.frame_review import regenerate_frame


def _zh() -> bool:
    return get_language() == "zh_CN"


def _t(vi: str, en: str) -> str:
    """Small inline vi/en helper for strings not in the i18n catalog yet."""
    return vi if not _zh() else en  # project i18n is zh/en; vi is our own addition, default to it


def _image_to_data_uri(path: str) -> str:
    """Read an image file and return it as a base64 data: URI for inline HTML embedding."""
    ext = os.path.splitext(path)[1].lstrip(".").lower() or "png"
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/{mime};base64,{b64}"


_CARD_CSS = """
<style>
:root {
    --pxv-accent: #ff4b4b;
    --pxv-accent-soft: rgba(255,75,75,0.15);
    --pxv-done: #21c15a;
    --pxv-done-soft: rgba(33,193,90,0.16);
}
.scene-card {
    border: 1px solid rgba(250,250,250,0.10);
    border-radius: 14px;
    overflow: hidden;
    background: rgba(250,250,250,0.03);
    box-shadow: 0 2px 10px rgba(0,0,0,0.18);
    transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
    margin-bottom: 0.55rem;
}
.scene-card:hover {
    border-color: rgba(250,250,250,0.28);
    transform: translateY(-2px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.28);
}
.scene-card .thumb-wrap {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: rgba(0,0,0,0.25);
    overflow: hidden;
    position: relative;
}
.scene-card .thumb-wrap img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
}
.scene-card .thumb-wrap.empty {
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(250,250,250,0.4);
    font-size: 0.85rem;
}
.scene-card .badge {
    position: absolute;
    top: 8px;
    left: 8px;
    font-size: 0.7rem;
    font-weight: 700;
    padding: 3px 10px;
    border-radius: 999px;
    letter-spacing: 0.01em;
    backdrop-filter: blur(2px);
}
.scene-card .badge.done {
    background: var(--pxv-done-soft);
    color: var(--pxv-done);
    border: 1px solid rgba(33,193,90,0.35);
}
.scene-card .badge.pending {
    background: rgba(250,250,250,0.12);
    color: rgba(250,250,250,0.85);
    border: 1px solid rgba(250,250,250,0.2);
}
.scene-card .scene-num {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(0,0,0,0.55);
    color: #fff;
    font-size: 0.72rem;
    font-weight: 700;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}
.scene-card .body {
    padding: 0.6rem 0.75rem 0.15rem 0.75rem;
}
.scene-card .narration {
    font-size: 0.82rem;
    line-height: 1.3;
    height: 2.6em;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: rgba(250,250,250,0.85);
    margin: 0;
}
/* Icon-only action buttons under each card: fixed square, never wrap text */
.scene-actions div[data-testid="stButton"] button {
    width: 100% !important;
    aspect-ratio: 1 / 1;
    padding: 0 !important;
    font-size: 1.1rem;
    border-radius: 10px !important;
    white-space: nowrap;
}
</style>
"""


def _do_regenerate(pixelle_video, storyboard, frame_index: int, regenerate_voice: bool = False):
    with st.spinner(f"Đang gen lại cảnh {frame_index + 1}..."):
        try:
            run_async(regenerate_frame(pixelle_video, storyboard, frame_index, regenerate_voice=regenerate_voice))
        except Exception as e:
            logger.exception(e)
            st.error(f"Gen lại cảnh {frame_index + 1} thất bại: {e}")


def _render_card_html(i: int, frame, pending: bool = False):
    """Build the HTML for one scene card. If pending=True (regen in progress
    or no image yet), render the skeleton state instead of the thumbnail."""
    thumb = None if pending else (frame.composed_image_path or frame.image_path)
    is_done = bool(frame.video_segment_path) and not pending
    badge_class = "done" if is_done else "pending"
    badge_text = "Xong" if is_done else ("Đang gen lại..." if pending else "Chưa xong")

    thumb_html = ""
    if thumb and os.path.exists(thumb):
        try:
            data_uri = _image_to_data_uri(thumb)
            thumb_html = f'<img src="{data_uri}" />'
        except Exception as e:
            logger.warning(f"Failed to embed thumbnail for frame {i}: {e}")

    narration_escaped = (frame.narration or "").replace("<", "&lt;").replace(">", "&gt;")
    placeholder_body = (
        '<div style="display:flex;align-items:center;justify-content:center;height:100%;">⏳ Đang xử lý...</div>'
        if pending else "⚠️ Chưa có ảnh"
    )

    return f"""
    <div class="scene-card">
        <div class="thumb-wrap{' empty' if not thumb_html else ''}">
            <span class="badge {badge_class}">{badge_text}</span>
            <span class="scene-num">{i + 1}</span>
            {thumb_html if thumb_html else placeholder_body}
        </div>
        <div class="body">
            <p class="narration">{narration_escaped}</p>
        </div>
    </div>
    """


@st.dialog("Xem cảnh", width="large")
def _zoom_dialog(pixelle_video, storyboard):
    frames = storyboard.frames
    i = st.session_state.get("review_selected_frame", 0)
    i = max(0, min(i, len(frames) - 1))
    frame = frames[i]

    thumb = frame.composed_image_path or frame.image_path
    if thumb and os.path.exists(thumb):
        st.image(thumb, use_container_width=True)
    else:
        st.warning("Cảnh này chưa có ảnh (có thể đang lỗi).")

    st.caption(f"Cảnh {i + 1}/{len(frames)}")
    st.markdown(f"*{frame.narration}*")

    nav_prev, nav_close, nav_next = st.columns(3)
    with nav_prev:
        if st.button("◀ Cảnh trước", disabled=(i == 0), use_container_width=True, key="dlg_prev"):
            st.session_state["review_selected_frame"] = i - 1
            st.rerun()
    with nav_close:
        if st.button("✖ Đóng", use_container_width=True, key="dlg_close"):
            st.session_state["zoom_dialog_open"] = False
            st.rerun()
    with nav_next:
        if st.button("Cảnh sau ▶", disabled=(i == len(frames) - 1), use_container_width=True, key="dlg_next"):
            st.session_state["review_selected_frame"] = i + 1
            st.rerun()

    st.markdown("---")

    # Editable image prompt - lets the user tweak the prompt for this exact
    # scene before regenerating, instead of only being able to regenerate
    # with whatever the LLM originally wrote.
    st.caption("✏️ Prompt ảnh của cảnh này (sửa rồi bấm Gen lại để dùng prompt mới):")
    edited_prompt = st.text_area(
        "Image prompt",
        value=frame.image_prompt or "",
        height=90,
        key=f"dlg_prompt_edit_{i}",
        label_visibility="collapsed"
    )

    if st.button("💾 Lưu & 🔄 Gen lại cảnh này", use_container_width=True, type="primary", key="dlg_regen"):
        frame.image_prompt = edited_prompt
        st.session_state["dlg_pending_frame"] = i
        st.rerun()


def _handle_pending_regen(pixelle_video, storyboard):
    """If a regen was just triggered from inside the zoom dialog, run it now
    (after the dialog's own rerun already reflects the edited prompt), then
    reopen the dialog on the same frame showing the fresh result."""
    pending_i = st.session_state.pop("dlg_pending_frame", None)
    if pending_i is None:
        return
    _do_regenerate(pixelle_video, storyboard, pending_i)
    st.session_state["review_selected_frame"] = pending_i
    st.session_state["zoom_dialog_open"] = True


def render_scene_review(pixelle_video, pipeline_name: str):
    """Render the scene review grid. Expects st.session_state['review_ctx'] to be set."""
    ctx = st.session_state.get("review_ctx")
    if ctx is None or ctx.storyboard is None:
        # Nothing to review (shouldn't normally happen) - bail back to the generate form.
        st.session_state["review_active"] = False
        st.rerun()
        return

    storyboard = ctx.storyboard
    frames = storyboard.frames

    st.markdown(_CARD_CSS, unsafe_allow_html=True)
    st.success(f"✅ Đã tạo xong {len(frames)} cảnh. Xem lại từng cảnh trước khi ghép video cuối.")
    st.caption("Cảnh nào chưa ưng thì bấm '🔄 Gen lại' — chỉ ảnh của cảnh đó được tạo lại, giọng đọc giữ nguyên.")

    # Pagination: for large videos (100s of scenes), rendering every card at
    # once would be very heavy (hundreds of HTML cards + button pairs). Only
    # render one page's worth at a time.
    PAGE_SIZE = 30
    n_pages = max(1, (len(frames) + PAGE_SIZE - 1) // PAGE_SIZE)
    if n_pages > 1:
        page_key = "review_grid_page"
        current_page = st.session_state.get(page_key, 1)
        current_page = max(1, min(current_page, n_pages))

        pg_prev, pg_label, pg_next = st.columns([1, 2, 1])
        with pg_prev:
            if st.button("◀ Trang trước", disabled=(current_page == 1), use_container_width=True, key="grid_page_prev"):
                st.session_state[page_key] = current_page - 1
                st.rerun()
        with pg_label:
            st.markdown(
                f"<div style='text-align:center; padding-top:0.4rem;'>Trang {current_page}/{n_pages} "
                f"(cảnh {(current_page-1)*PAGE_SIZE + 1}-{min(current_page*PAGE_SIZE, len(frames))} / {len(frames)})</div>",
                unsafe_allow_html=True
            )
        with pg_next:
            if st.button("Trang sau ▶", disabled=(current_page == n_pages), use_container_width=True, key="grid_page_next"):
                st.session_state[page_key] = current_page + 1
                st.rerun()

        st.session_state[page_key] = current_page
        page_start = (current_page - 1) * PAGE_SIZE
        page_end = min(page_start + PAGE_SIZE, len(frames))
    else:
        page_start = 0
        page_end = len(frames)

    n_cols = 3
    cols = st.columns(n_cols)
    card_placeholders = {}
    for i in range(page_start, page_end):
        frame = frames[i]
        with cols[(i - page_start) % n_cols]:
            card_placeholders[i] = st.empty()
            card_placeholders[i].markdown(_render_card_html(i, frame), unsafe_allow_html=True)

            st.markdown('<div class="scene-actions">', unsafe_allow_html=True)
            btn_zoom, btn_regen = st.columns(2)
            with btn_zoom:
                if st.button("🔍", key=f"zoom_{i}", use_container_width=True, help="Xem lớn"):
                    st.session_state["review_selected_frame"] = i
                    st.session_state["zoom_dialog_open"] = True
                    st.rerun()
            with btn_regen:
                if st.button("🔄", key=f"regen_{i}", use_container_width=True, help="Gen lại cảnh này"):
                    # Show the skeleton state immediately (before the blocking
                    # regenerate call finishes), same trick used by the live
                    # generation grid - update the placeholder in place.
                    card_placeholders[i].markdown(_render_card_html(i, frame, pending=True), unsafe_allow_html=True)
                    _do_regenerate(pixelle_video, storyboard, i)
                    card_placeholders[i].markdown(_render_card_html(i, frame), unsafe_allow_html=True)
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Handle a regen requested from inside the zoom dialog (prompt edit +
    # "Save & Regenerate"), then reopen the dialog on the same frame.
    _handle_pending_regen(pixelle_video, storyboard)

    # Keep the dialog open across reruns (prev/next/regen inside it) by
    # calling it unconditionally whenever the flag is set, instead of only
    # gating it behind the 🔍 button's own click event.
    if st.session_state.get("zoom_dialog_open"):
        _zoom_dialog(pixelle_video, storyboard)

    st.markdown("---")

    action_cancel, action_compose = st.columns(2)
    with action_cancel:
        if st.button("❌ Huỷ, làm lại từ đầu", use_container_width=True):
            st.session_state["review_active"] = False
            st.session_state.pop("review_ctx", None)
            st.session_state.pop("review_selected_frame", None)
            st.rerun()

    with action_compose:
        if st.button("✅ Ghép video cuối", type="primary", use_container_width=True):
            pipeline_instance = pixelle_video.pipelines[pipeline_name]
            progress = st.progress(0)
            status = st.empty()
            status.text("Đang ghép video...")
            try:
                result = run_async(pipeline_instance.compose_and_finalize(ctx))
                progress.progress(100)
                status.text("Xong!")

                st.session_state["review_active"] = False
                st.session_state.pop("review_ctx", None)
                st.session_state.pop("review_selected_frame", None)
                st.session_state["last_composed_result"] = result
                st.rerun()
            except Exception as e:
                progress.empty()
                status.empty()
                st.error(f"Ghép video thất bại: {e}")
                logger.exception(e)


def render_last_result_if_any():
    """After compose_and_finalize succeeds, show the final video once."""
    result = st.session_state.get("last_composed_result")
    if not result:
        return

    st.markdown("---")
    st.markdown(f"**{tr('section.video_generation')}**")

    file_size_mb = result.file_size / (1024 * 1024)
    st.caption(
        f"📦 {file_size_mb:.2f}MB   🎬 {len(result.storyboard.frames)} cảnh"
    )

    if os.path.exists(result.video_path):
        st.video(result.video_path)
        with open(result.video_path, "rb") as video_file:
            video_bytes = video_file.read()
            video_filename = os.path.basename(result.video_path)
            st.download_button(
                label="⬇️ 下载视频" if _zh() else "⬇️ Download Video",
                data=video_bytes,
                file_name=video_filename,
                mime="video/mp4",
                use_container_width=True,
                key="last_result_download"
            )
    else:
        st.error(f"Không tìm thấy file video: {result.video_path}")

    if st.button("🆕 Tạo video mới", use_container_width=True):
        st.session_state.pop("last_composed_result", None)
        st.rerun()
