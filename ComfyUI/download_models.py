#!/usr/bin/env python3
"""
Tải các file model cần thiết cho workflow Flux.2-Klein 4B (fp8) vào đúng
thư mục ComfyUI/models/...

Cách dùng:
    1. Cài thư viện cần thiết (chạy 1 lần):
         pip install -U huggingface_hub

    2. Lấy Access Token trên HuggingFace:
         - Đăng nhập huggingface.co -> Settings -> Access Tokens -> New Token
         - Loại: Read là đủ
         - QUAN TRỌNG: vào thẳng link sau và bấm "Agree" để được phép tải
           model gated (chỉ cần làm 1 lần):
           https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8

    3. Set token vào biến môi trường rồi chạy script:
         # Windows (PowerShell)
         $env:HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxx"
         python download_models.py

         # Linux / máy ảo cloud
         export HF_TOKEN="hf_xxxxxxxxxxxxxxxxxxxx"
         python3 download_models.py

    Mặc định script tự tìm thư mục "ComfyUI" nằm CÙNG CẤP với file script
    này (ví dụ: Pixelle-Video/ComfyUI/). Nếu cấu trúc thư mục khác, sửa
    biến COMFYUI_DIR bên dưới hoặc set biến môi trường COMFYUI_DIR.
"""

import os
import shutil
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print("Chưa cài huggingface_hub. Đang tự cài đặt...")
    os.system(f"{sys.executable} -m pip install -U huggingface_hub")
    from huggingface_hub import hf_hub_download


# ============ CẤU HÌNH ============

# Thư mục gốc ComfyUI. Mặc định: cùng cấp với file script này.
COMFYUI_DIR = Path(os.environ.get("COMFYUI_DIR", Path(__file__).resolve().parent / "ComfyUI"))

HF_TOKEN = os.environ.get("HF_TOKEN")

# Danh sách file cần tải: (repo_id, subfolder trên HF, tên file, thư mục đích trong models/, cần token không)
FILES_TO_DOWNLOAD = [
    {
        "label": "Diffusion model (Flux.2 Klein 4B fp8)",
        "repo_id": "black-forest-labs/FLUX.2-klein-4b-fp8",
        "subfolder": None,
        "filename": "flux-2-klein-4b-fp8.safetensors",
        "dest_subdir": "diffusion_models",
        "gated": True,
    },
    {
        "label": "Text encoder (Qwen3-4B)",
        "repo_id": "Comfy-Org/vae-text-encorder-for-flux-klein-4b",
        "subfolder": "split_files/text_encoders",
        "filename": "qwen_3_4b.safetensors",
        "dest_subdir": "text_encoders",
        "gated": False,
    },
    {
        "label": "VAE (Flux.2 chung)",
        "repo_id": "Comfy-Org/flux2-dev",
        "subfolder": "split_files/vae",
        "filename": "flux2-vae.safetensors",
        "dest_subdir": "vae",
        "gated": False,
    },
]


def human_size(num_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f}{unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f}TB"


def download_one(item: dict) -> None:
    dest_dir = COMFYUI_DIR / "models" / item["dest_subdir"]
    dest_dir.mkdir(parents=True, exist_ok=True)
    final_path = dest_dir / item["filename"]

    if final_path.exists():
        print(f"[BỎ QUA] {item['label']} đã tồn tại tại: {final_path}")
        return

    if item["gated"] and not HF_TOKEN:
        print(
            f"[LỖI] {item['label']} cần Access Token (biến HF_TOKEN) vì model "
            f"này yêu cầu đăng nhập + đồng ý license. "
            f"Vào https://huggingface.co/{item['repo_id']} để accept trước."
        )
        return

    print(f"[ĐANG TẢI] {item['label']} ...")
    try:
        downloaded_path = hf_hub_download(
            repo_id=item["repo_id"],
            filename=item["filename"],
            subfolder=item["subfolder"],
            token=HF_TOKEN if item["gated"] else HF_TOKEN,  # token cũng ok cho repo public
            local_dir=str(dest_dir if item["subfolder"] is None else COMFYUI_DIR / "models" / "_tmp_dl"),
        )

        # Nếu file được tải kèm subfolder, cấu trúc thư mục sẽ là
        # _tmp_dl/split_files/text_encoders/xxx.safetensors -> cần move ra đúng vị trí
        downloaded_path = Path(downloaded_path)
        if downloaded_path.resolve() != final_path.resolve():
            shutil.move(str(downloaded_path), str(final_path))

        size = final_path.stat().st_size
        print(f"[XONG] {item['label']} -> {final_path} ({human_size(size)})")
    except Exception as e:
        print(f"[LỖI] Không tải được {item['label']}: {e}")


def cleanup_tmp():
    tmp_dir = COMFYUI_DIR / "models" / "_tmp_dl"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    print(f"Thư mục ComfyUI đang dùng: {COMFYUI_DIR}")
    if not COMFYUI_DIR.exists():
        print(f"[CẢNH BÁO] Không tìm thấy thư mục {COMFYUI_DIR}. "
              f"Kiểm tra lại đường dẫn hoặc set biến môi trường COMFYUI_DIR.")

    for item in FILES_TO_DOWNLOAD:
        download_one(item)

    cleanup_tmp()
    print("\nHoàn tất. Kiểm tra lại 3 file trong ComfyUI/models/diffusion_models, "
          "text_encoders, vae trước khi chạy workflow.")


if __name__ == "__main__":
    main()
