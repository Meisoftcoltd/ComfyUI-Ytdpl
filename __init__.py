import os
import sys
import subprocess
import shutil
import time
import importlib.util
from pathlib import Path
from typing import Tuple

# === AUTO-INYECCIÓN DE DENO EN EL PATH (Vital para WSL2) ===
USER_HOME = Path.home()
deno_path = str(USER_HOME / ".deno" / "bin")
if deno_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{deno_path}:{os.environ.get('PATH', '')}"

def install_missing_requirements():
    requirements = [
        ("yt-dlp", "yt_dlp"),
        ("curl-cffi", "curl_cffi"),
        ("numpy", "numpy"),
        ("opencv-python", "cv2"),
        ("websockets", "websockets"),
    ]

    missing = []
    for pkg, imp in requirements:
        if importlib.util.find_spec(imp) is None:
            missing.append(pkg)

    if missing:
        print(f"📥 ComfyUI-Ytdpl: Instalando dependencias faltantes: {missing}")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing, "yt-dlp-ejs"])
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
        self.output_dir = Path(__file__).parent.parent.parent / "output" / "ytdpl"
        self.output_dir.mkdir(parents=True, exist_ok=True)

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
                "cookies_text": ("STRING", {"multiline": True, "default": ""}),
                "cookies_file": (cookie_files, ),
                "browser_source": (["Ninguno", "Chrome", "Firefox", "Safari", "Edge"], {"default": "Ninguno"}),
                "update_yt_dlp": ("BOOLEAN", {"default": False}),
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
        return f"bestvideo[height<={h}][ext={ext}]+bestaudio[ext=m4a]/best[height<={h}][ext={ext}]/best"

    def download_video(self, url, cookies_text, cookies_file, browser_source, update_yt_dlp, quality, format):
        if update_yt_dlp:
            print("🔄 ComfyUI-Ytdpl: Iniciando actualización forzada a NIGHTLY y motor EJS...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install",
                    "--no-cache-dir", "-U", "--pre",
                    "yt-dlp[default]", "yt-dlp-ejs", "curl_cffi", "websockets", "--break-system-packages"
                ])
                print("✅ ComfyUI-Ytdpl: Actualización completada.")
            except subprocess.CalledProcessError as e:
                raise Exception(f"❌ Error crítico al actualizar yt-dlp: {str(e)}\nRevisa tu conexión a internet.")
            except Exception as e:
                raise Exception(f"❌ Error inesperado al actualizar: {str(e)}")

        if not url.strip():
            raise Exception("❌ La URL está vacía.")

        dest_path = self.output_dir

        is_audio = format in ["mp3", "m4a", "wav", "flac", "ogg", "opus", "aac"]

        # === LÓGICA DE COOKIES ===
        cookie_path_to_use = None

        if cookies_text and cookies_text.strip():
            cookie_path_to_use = self.cookies_dir / "cookies_pegadas.txt"
            try:
                with open(cookie_path_to_use, 'w', encoding='utf-8') as f:
                    f.write(cookies_text)
                print(f"🍪 Cookies creadas y guardadas permanentemente en: {cookie_path_to_use.name}")
            except Exception as e:
                raise Exception(f"❌ Error al guardar las cookies en input/cookies: {e}")

        elif cookies_file != "Ninguno":
            c_path = self.cookies_dir / cookies_file
            if c_path.exists():
                cookie_path_to_use = c_path
                print(f"🍪 Usando archivo de cookies existente: {c_path.name}")
            else:
                print(f"⚠️ El archivo {cookies_file} no existe. Continuando sin cookies.")

        def build_cmd(q_val, get_filename=False):
            f_str = self.get_format_string(q_val, format, is_audio)
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-f", f_str,
                "--restrict-filenames",
                "-P", str(dest_path),
                "--no-overwrites",
                "--yes-playlist", 
                "--remote-components", "ejs:github"
            ]

            if cookie_path_to_use:
                cmd.extend(["--cookies", str(cookie_path_to_use)])
                cmd.extend(["--extractor-args", "youtube:player_client=tv_downgraded,web"])
            else:
                cmd.extend(["--extractor-args", "youtube:player_client=android,tv"])

            # === CAMBIO: USAR NOMBRES GENÉRICOS DE NAVEGADOR PARA CURL-CFFI ===
            if browser_source != "Ninguno":
                browser_map = {
                    "Chrome": "chrome",
                    "Firefox": "firefox",
                    "Safari": "safari",
                    "Edge": "edge"
                }
                target = browser_map.get(browser_source)
                if target:
                    cmd.extend(["--impersonate", target])

            if get_filename:
                cmd.append("--get-filename")
            
            if not is_audio: 
                cmd.extend(["--merge-output-format", format])
            
            cmd.append(url)
            return cmd

        print(f"🔍 Calculando nombre de archivo para: {url}")

        cmd_filename = build_cmd(quality, get_filename=True)
        filename_res = subprocess.run(cmd_filename, capture_output=True, text=True, timeout=1800)

        selected_quality = quality

        if filename_res.returncode != 0 and quality != "best":
            print(f"⚠️ No se pudo calcular nombre para '{quality}'. Probando con 'best'...")
            selected_quality = "best"
            cmd_filename = build_cmd("best", get_filename=True)
            filename_res = subprocess.run(cmd_filename, capture_output=True, text=True, timeout=1800)

        if filename_res.returncode != 0:
            error_stderr = filename_res.stderr or ""
            error_stderr_lower = error_stderr.lower()
            if any(x in error_stderr_lower for x in ["captcha", "403", "forbidden", "verify", "sign in", "private"]):
                raise Exception("🛑 TikTok/YouTube pide Captcha o Login. Pega un texto nuevo en el campo 'cookies_text'.")
            
            if "permission denied" in error_stderr_lower:
                raise Exception(f"🛑 Error de permisos con el archivo de cookies seleccionado ({cookies_file}). SOLUCIÓN: Abre ese archivo en texto plano, copia todo, pégalo en el cajón 'cookies_text' de ComfyUI y borra el archivo original problemático.")
                
            raise Exception(f"🛑 Error al obtener información del video:\n{error_stderr[-200:]}")

        expected_filename = filename_res.stdout.strip().splitlines()[-1] 
        expected_path = Path(expected_filename)
        print(f"🎯 Archivo esperado: {expected_path.name}")

        print(f"📥 Iniciando descarga ({selected_quality})...")
        cmd_dl = build_cmd(selected_quality, get_filename=False)
        
        print("\n--- Registro de yt-dlp (ComfyUI) ---")
        proc = subprocess.Popen(cmd_dl, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        output_lines = []
        for line in proc.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            output_lines.append(line)
        
        proc.wait()
        output = "".join(output_lines)
        print("------------------------------------\n")

        if proc.returncode == 0:
            if expected_path.exists():
                 return (str(expected_path), f"✅ Éxito: {expected_path.name}")
            else:
                 print("⚠️ Archivo predicho no encontrado, buscando el más reciente...")
                 files = list(dest_path.glob("*.*"))
                 if not files: raise Exception("Archivo no encontrado tras descarga exitosa.")
                 latest_file = max(files, key=lambda f: f.stat().st_mtime)
                 return (str(latest_file), f"✅ Éxito (Fallback): {latest_file.name}")
        else:
            error_stderr_lower = output.lower()
            if any(x in error_stderr_lower for x in ["captcha", "403", "forbidden", "verify", "sign in", "js challenge", "private"]):
                raise Exception("🛑 YouTube/TikTok bloqueó la descarga (Requiere Sesión/Captcha). Pega tu texto de cookies actualizado en el nodo.")

            raise Exception(f"🛑 Error final de descarga:\n{output[-200:]}")

NODE_CLASS_MAPPINGS = {"YTDLPVideoDownloader": YTDLPVideoDownloader}
NODE_DISPLAY_NAME_MAPPINGS = {"YTDLPVideoDownloader": "YT-DLP Downloader (Auto-Quality) 📥"}
