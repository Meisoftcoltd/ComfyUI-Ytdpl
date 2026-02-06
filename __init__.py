import os
import sys
import subprocess
import shutil
import time
import webbrowser
import importlib.util
from pathlib import Path
from typing import Tuple

def install_missing_requirements():
    requirements = [
        ("yt-dlp", "yt_dlp"),
        ("curl-cffi", "curl_cffi"),
        ("numpy", "numpy"),
        ("opencv-python", "cv2"),
    ]

    missing = []
    for pkg, imp in requirements:
        if importlib.util.find_spec(imp) is None:
            missing.append(pkg)

    if missing:
        print(f"📥 ComfyUI-Ytdpl: Instalando dependencias faltantes: {missing}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing])
            print("✅ Dependencias instaladas correctamente.")
        except Exception as e:
            print(f"❌ Error al instalar dependencias: {e}")

# Ejecutar verificación de requisitos al importar el nodo
install_missing_requirements()

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

        formats = [
            "mp4", "mkv", "webm", "mov", "avi", "flv", "3gp", "ts", "m4v",
            "mp3", "m4a", "wav", "flac", "ogg", "opus", "aac", "mka"
        ]

        return {
            "required": {
                "url": ("STRING", {"multiline": False, "default": ""}),
                "cookies_file": (cookie_files, ),
                "update_yt_dlp": ("BOOLEAN", {"default": False}),
                "output_dir": ("STRING", {"multiline": False, "default": "input"}),
                "filename_template": ("STRING", {"multiline": False, "default": "%(title)s.%(ext)s"}),
                "quality": (["best", "1080p", "720p", "480p", "360p"], {"default": "best"}),
                "format": (formats, {"default": "mp4"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("video_path", "info")
    FUNCTION = "download_video"
    CATEGORY = "video/download"

    def get_format_string(self, quality, ext, is_audio):
        if is_audio:
            return f"bestaudio[ext={ext}]/bestaudio/best"
        if quality == "best":
            return "bestvideo+bestaudio/best"

        h = quality.replace("p", "")
        # Selector robusto: intenta la altura pero permite caer a lo mejor disponible
        return f"bestvideo[height<={h}][ext={ext}]+bestaudio[ext=m4a]/best[height<={h}][ext={ext}]/best"

    def download_video(self, url, cookies_file, update_yt_dlp, output_dir, filename_template, quality, format):
        start_time = time.time()

        if update_yt_dlp:
            print("🔄 ComfyUI-Ytdpl: Iniciando actualización forzada a NIGHTLY...")
            try:
                # Usamos check_call para que si falla, lance una excepción visible y detenga el nodo
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "--no-cache-dir",     # Evita usar caché vieja
                    "-U",                 # Force upgrade
                    "https://github.com/yt-dlp/yt-dlp/archive/master.zip"
                ])
                print("✅ ComfyUI-Ytdpl: Actualización Nightly completada.")
            except subprocess.CalledProcessError as e:
                # Hacemos el error visible al usuario en la UI
                raise Exception(f"❌ Error crítico al actualizar yt-dlp: {str(e)}\nRevisa tu conexión a internet.")
            except Exception as e:
                raise Exception(f"❌ Error inesperado al actualizar: {str(e)}")

        if not url.strip():
            raise Exception("❌ La URL está vacía.")

        dest_path = self.base_input_path if output_dir == "input" else Path(output_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        # SECURITY CHECK
        if Path(filename_template).is_absolute():
             raise Exception("❌ Error de Seguridad: filename_template no puede ser una ruta absoluta.")

        try:
            full_output_path = (dest_path / filename_template).resolve()
            resolved_dest = dest_path.resolve()
            if not full_output_path.is_relative_to(resolved_dest):
                 raise Exception("❌ Error de Seguridad: filename_template intenta salir del directorio de destino.")
        except Exception as e:
             if "Error de Seguridad" in str(e): raise
             # Si falla resolve() es posible que la ruta no sea válida, lo cual es otro tipo de error
             # pero por seguridad asumimos lo peor si no podemos validarlo
             raise Exception(f"❌ Error al validar ruta de salida: {str(e)}")

        is_audio = format in ["mp3", "m4a", "wav", "flac", "ogg", "opus", "aac"]

        # --- FUNCIÓN INTERNA PARA CONSTRUIR EL COMANDO ---
        def build_cmd(q_val, get_filename=False):
            f_str = self.get_format_string(q_val, format, is_audio)
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", f_str,
                "--restrict-filenames",
                "--no-overwrites",
                "-o", str(dest_path / filename_template),
                "--no-playlist",
                "--extractor-args", "youtube:player_client=android,ios",
                "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
            if get_filename:
                cmd.append("--get-filename")
            if not is_audio: cmd.extend(["--merge-output-format", format])
            if cookies_file != "Ninguno":
                c_path = self.cookies_dir / cookies_file
                if c_path.exists(): cmd.extend(["--cookies", str(c_path)])
            cmd.append(url)
            return cmd

        # --- PASO 1: OBTENER NOMBRE DE ARCHIVO ESPERADO ---
        print(f"🔍 Calculando nombre de archivo para: {url}")

        # Primero intentamos obtener el nombre con la calidad seleccionada
        # Timeout aumentado a 30 mins para listas grandes
        cmd_filename = build_cmd(quality, get_filename=True)
        filename_res = subprocess.run(cmd_filename, capture_output=True, text=True, timeout=1800)

        selected_quality = quality

        # Si falla obtener nombre (ej. formato no disponible), intentamos con 'best' si no era ya 'best'
        if filename_res.returncode != 0 and quality != "best":
            print(f"⚠️ No se pudo calcular nombre para '{quality}'. Probando con 'best'...")
            selected_quality = "best"
            cmd_filename = build_cmd("best", get_filename=True)
            filename_res = subprocess.run(cmd_filename, capture_output=True, text=True, timeout=1800)

        if filename_res.returncode != 0:
             # Si falla incluso calculando nombre, probablemente sea error de red o bloqueo
            error_stderr = filename_res.stderr or ""
            if any(x in error_stderr.lower() for x in ["captcha", "403", "forbidden", "verify"]):
                webbrowser.open(url)
                raise Exception("🛑 TikTok/YouTube pide Captcha. Resuélvelo en el navegador y reintenta.")
            raise Exception(f"🛑 Error al obtener información del video:\n{error_stderr[-200:]}")

        expected_filename = filename_res.stdout.strip().splitlines()[-1] # Tomamos la última línea por si hay warnings
        expected_path = Path(expected_filename)
        print(f"🎯 Archivo esperado: {expected_path.name}")

        # --- PASO 2: DESCARGAR ---
        print(f"📥 Iniciando descarga ({selected_quality})...")
        cmd_dl = build_cmd(selected_quality, get_filename=False)
        # Timeout aumentado a 24 horas para canales completos
        result = subprocess.run(cmd_dl, capture_output=True, text=True, timeout=86400)

        # --- GESTIÓN DE RESULTADOS ---
        if result.returncode == 0:
            if expected_path.exists():
                 return (str(expected_path), f"✅ Éxito: {expected_path.name}")
            else:
                 # Fallback raro: yt-dlp dijo OK pero el archivo predicho no está.
                 # Buscamos el más reciente como último recurso, pero avisando.
                 print("⚠️ Archivo predicho no encontrado, buscando el más reciente...")
                 files = list(dest_path.glob("*.*"))
                 if not files: raise Exception("Archivo no encontrado tras descarga exitosa.")
                 latest_file = max(files, key=lambda f: f.stat().st_mtime)
                 return (str(latest_file), f"✅ Éxito (Fallback): {latest_file.name}")
        else:
            error_stderr = result.stderr or ""
            if any(x in error_stderr.lower() for x in ["captcha", "403", "forbidden", "verify"]):
                webbrowser.open(url)
                raise Exception("🛑 TikTok/YouTube pide Captcha durante descarga.")

            raise Exception(f"🛑 Error final de descarga:\n{error_stderr[-200:]}")

NODE_CLASS_MAPPINGS = {"YTDLPVideoDownloader": YTDLPVideoDownloader}
NODE_DISPLAY_NAME_MAPPINGS = {"YTDLPVideoDownloader": "YT-DLP Downloader (Auto-Quality) 📥"}
