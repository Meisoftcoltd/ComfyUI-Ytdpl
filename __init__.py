import os
import sys
import subprocess
import shutil
import time
from pathlib import Path
from typing import Tuple

class YTDLPVideoDownloader:
    def __init__(self):
        self.base_input_path = Path(__file__).parent.parent.parent / "input"
        self.cookies_dir = self.base_input_path / "cookies"
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
        
    @classmethod
    def INPUT_TYPES(cls):
        cookies_folder = Path(__file__).parent.parent.parent / "input" / "cookies"
        cookies_folder.mkdir(parents=True, exist_ok=True)
        cookie_files = [f.name for f in cookies_folder.glob("*.txt")]
        if not cookie_files: cookie_files = ["Ninguno"]

        return {
            "required": {
                "url": ("STRING", {"multiline": False, "default": ""}),
                "cookies_file": (cookie_files, ),
                "force_update": ("BOOLEAN", {"default": True}), # Opción para controlar la actualización
                "output_dir": ("STRING", {"multiline": False, "default": "input"}),
                "filename_template": ("STRING", {"multiline": False, "default": "%(title)s.%(ext)s"}),
                "quality": (["best", "1080p", "720p", "480p", "360p"], {"default": "best"}),
                "format": (["mp4", "mkv", "webm"], {"default": "mp4"}),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_path", "info")
    FUNCTION = "download_video"
    CATEGORY = "video/download"

    def download_video(self, url, cookies_file, force_update, output_dir, filename_template, quality, format):
        start_time = time.time()
        
        # --- PASO 0: ACTUALIZACIÓN EN TIEMPO REAL ---
        if force_update:
            print("🔄 Verificando actualizaciones de YT-DLP antes de descargar...")
            try:
                # Ejecutamos pip install -U de forma silenciosa pero efectiva
                subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "-U", "yt-dlp"])
                print("✅ YT-DLP está en la última versión.")
            except Exception as e:
                print(f"⚠️ No se pudo actualizar en este paso: {e}")

        # 1. Validar URL
        if not url.strip():
            raise Exception("❌ La URL está vacía.")

        # 2. Configurar rutas
        dest_path = self.base_input_path if output_dir == "input" else Path(output_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        # 3. Configurar calidad y formato
        if quality == "best":
            format_str = f"bestvideo[ext={format}]+bestaudio[ext=m4a]/best[ext={format}]/best"
        else:
            h = quality.replace("p", "")
            format_str = f"bestvideo[height<={h}][ext={format}]+bestaudio[ext=m4a]/best[height<={h}]"

        # 4. Construir comando
        command = [
            sys.executable, "-m", "yt_dlp",
            "-f", format_str,
            "--merge-output-format", format,
            "--restrict-filenames",
            "--no-overwrites",
            "-o", str(dest_path / filename_template),
            "--no-playlist"
        ]

        if cookies_file != "Ninguno":
            c_path = self.cookies_dir / cookies_file
            if c_path.exists():
                command.extend(["--cookies", str(c_path)])

        command.append(url)

        try:
            print(f"📥 Descargando: {url}")
            result = subprocess.run(command, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Buscar el archivo descargado
                files = list(dest_path.glob("*.*"))
                if not files: raise Exception("Archivo no encontrado tras descarga.")
                
                latest_file = max(files, key=lambda f: f.stat().st_mtime)
                info = f"✅ Éxito: {latest_file.name} ({time.time()-start_time:.1f}s)"
                return (str(latest_file), info)
            
            else:
                error_stderr = result.stderr or ""
                # Si falla, lanzamos el error para que ComfyUI se detenga
                raise Exception(f"🛑 Error de descarga:\n{error_stderr[-500:]}")

        except Exception as e:
            raise Exception(f"🛑 Error Crítico: {str(e)}")

NODE_CLASS_MAPPINGS = {"YTDLPVideoDownloader": YTDLPVideoDownloader}
NODE_DISPLAY_NAME_MAPPINGS = {"YTDLPVideoDownloader": "YT-DLP Downloader (Auto-Update) 📥"}