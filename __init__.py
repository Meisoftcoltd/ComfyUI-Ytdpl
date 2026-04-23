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
    # 🚀 FIX: Mapeo exacto entre el nombre en pip y el módulo interno del plugin
    requirements = [
        ("yt-dlp", "yt_dlp"),
        ("curl-cffi", "curl_cffi"),
        ("numpy", "numpy"),
        ("opencv-python", "cv2"),
        ("websockets", "websockets"),
        ("playwright", "playwright"),
        ("yt-dlp-ejs", "yt_dlp_plugins.extractor.ejs"),
        ("bgutil-ytdlp-pot-provider", "yt_dlp_plugins.extractor.getpot_bgutil")
    ]

    missing = []
    for pkg, imp in requirements:
        try:
            if importlib.util.find_spec(imp) is None:
                missing.append(pkg)
        except ModuleNotFoundError:
            missing.append(pkg)

    if missing:
        print(f"📥 ComfyUI-Ytdpl: Instalando dependencias faltantes: {missing}")
        try:
            # 🚀 FIX: Pasamos el array limpio 'missing' sin forzar sufijos problemáticos
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", *missing])
            print("✅ Dependencias instaladas correctamente.")
            if "playwright" in missing:
                print("📥 Instalando navegadores de Playwright...")
                subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
                print("✅ Navegadores de Playwright instalados.")
        except Exception as e:
            print(f"❌ Error al instalar dependencias: {e}")

# Ejecutar verificación de requisitos al importar el nodo
install_missing_requirements()

def get_cookies_interactively(url, save_path):
    from playwright.sync_api import sync_playwright
    import platform

    print("\n" + "="*60)
    print("🌐 [AUTO-COOKIE] Abriendo navegador para intervención manual...")
    print(f"🖥️ Sistema detectado: {platform.system()}")
    print("👉 POR FAVOR: Resuelve el Captcha o inicia sesión en la ventana.")
    print("👉 IMPORTANTE: Cuando el video empiece a reproducirse, CIERRA LA VENTANA.")
    print("="*60 + "\n")

    try:
        with sync_playwright() as p:
            # En Windows/Mac abrirá su ventana nativa. En Linux usará X11/Wayland/WSLg.
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)

            # Esperar a que el usuario cierre la ventana
            try:
                page.wait_for_event("close", timeout=0)
            except Exception:
                pass # Ventana cerrada por el usuario

            print("⚙️ [AUTO-COOKIE] Extrayendo sesión...")
            cookies = context.cookies()

            # Convertir a formato Netscape (yt-dlp compatible)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write("# Netscape HTTP Cookie File\n")
                for c in cookies:
                    domain = c.get('domain', '')
                    include_subdomains = 'TRUE' if domain.startswith('.') else 'FALSE'
                    path_val = c.get('path', '/')
                    secure = 'TRUE' if c.get('secure', False) else 'FALSE'
                    expires = str(int(c.get('expires', 0)))
                    name = c.get('name', '')
                    value = c.get('value', '')
                    f.write(f"{domain}\t{include_subdomains}\t{path_val}\t{secure}\t{expires}\t{name}\t{value}\n")

            browser.close()
        print("✅ [AUTO-COOKIE] Cookies guardadas con éxito. Reintentando descarga...")
        return True

    except Exception as e:
        print(f"\n⚠️ [AUTO-COOKIE] Interfaz gráfica no disponible: {e}")
        print("👉 (Esto es normal en servidores remotos sin pantalla o configuraciones estrictas).")
        return False

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

    RETURN_TYPES = ("*", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("video_path", "info", "title", "description", "thumbnail_url", "channel")
    FUNCTION = "download_video"
    CATEGORY = "video/download"

    @classmethod
    def IS_CHANGED(cls, url, cookies_text, cookies_file, browser_source, update_yt_dlp, quality, format):
        import hashlib
        state_string = f"{url}_{cookies_text}_{cookies_file}_{browser_source}_{quality}_{format}"
        m = hashlib.sha256()
        m.update(state_string.encode('utf-8'))
        return m.digest().hex()

    def get_format_string(self, quality, ext, is_audio):
        if is_audio:
            return "bestaudio/best"

        # 🚀 FIX OOM/FFprobe: Priorizar un archivo ÚNICO pre-mezclado (best) con H.264.
        # Evita que FFmpeg intente fusionar pistas separadas, lo que causa "Killed" (Falta de RAM) o errores de FFprobe.
        single_avc = "best[vcodec*=avc]"
        v_avc = "bestvideo[vcodec*=avc]"

        if quality == "best":
            return f"{single_avc}/{v_avc}+bestaudio/best"

        h = quality.replace("p", "")
        return f"{single_avc}[height<={h}][ext={ext}]/{v_avc}[height<={h}][ext={ext}]+bestaudio/best[height<={h}][ext={ext}]/best"

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

        auto_cookie_path = self.cookies_dir / "auto_cookies.txt"

        for attempt in range(2):
            try:
                def build_cmd(q_val, get_filename=False):
                    f_str = self.get_format_string(q_val, format, is_audio)
                    cmd = [
                        sys.executable, "-m", "yt_dlp",
                        "-f", f_str,
                        "--restrict-filenames",
                        "-P", str(dest_path),
                        "--no-overwrites",
                        "--yes-playlist",
                        "--ignore-errors",
                        "--remote-components", "ejs:github"
                    ]

                    if is_audio and not get_filename:
                        cmd.extend(["-x", "--audio-format", format])

                    if cookie_path_to_use:
                        cmd.extend(["--cookies", str(cookie_path_to_use)])
                        cmd.extend(["--extractor-args", "youtube:player_client=tv_downgraded,web;po_token=web+bgutil"])
                    else:
                        cmd.extend(["--extractor-args", "youtube:player_client=android,tv;po_token=web+bgutil"])

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

                    # Pedir a yt-dlp que genere un archivo con todos los metadatos
                    cmd.append("--write-info-json")

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
                    if "permission denied" in error_stderr_lower:
                        raise Exception(f"🛑 Error de permisos con el archivo de cookies seleccionado ({cookies_file}). SOLUCIÓN: Abre ese archivo en texto plano, copia todo, pégalo en el cajón 'cookies_text' de ComfyUI y borra el archivo original problemático.")
                    raise Exception(f"YT_DLP_ERROR: {error_stderr}")

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
                    final_path = None
                    if expected_path.exists():
                        final_path = expected_path
                    else:
                        print("⚠️ Archivo predicho no encontrado, buscando el más reciente...")
                        # Filtramos los .json para no seleccionar el archivo de metadatos por error
                        files = [f for f in dest_path.glob("*.*") if not f.name.endswith(".json")]
                        if not files: raise Exception("Archivo de video no encontrado tras descarga exitosa.")
                        final_path = max(files, key=lambda f: f.stat().st_mtime)

                    if is_audio:
                        actual_ext = final_path.suffix.lower().lstrip(".")
                        audio_formats = ["mp3", "m4a", "wav", "flac", "ogg", "opus", "aac", "mka"]
                        if actual_ext not in audio_formats:
                            raise Exception("❌ El vídeo se descargó correctamente pero no se encontró ninguna pista de audio para extraer. (Posible vídeo mudo de TikTok/YouTube).")

                    # --- Leer metadatos del JSON ---
                    title, description, thumbnail_url, channel = "", "", "", ""
                    import json
                    json_path = final_path.with_suffix('.info.json')

                    if json_path.exists():
                        try:
                            with open(json_path, 'r', encoding='utf-8') as f:
                                meta = json.load(f)
                                title = meta.get("title", "")
                                description = meta.get("description", "")
                                thumbnail_url = meta.get("thumbnail", "")
                                channel = meta.get("uploader", "")
                            os.remove(json_path)
                        except Exception as e:
                            print(f"⚠️ Error leyendo metadatos JSON: {e}")

                    return (str(final_path), f"✅ Éxito: {final_path.name}", title, description, thumbnail_url, channel)
                else:
                    raise Exception(f"YT_DLP_ERROR: {output}")

            except Exception as e:
                error_msg = str(e).lower()
                if "yt_dlp_error:" in error_msg:
                    # Check for blocking keywords
                    if any(x in error_msg for x in ["captcha", "403", "forbidden", "verify", "sign in", "js challenge", "private"]):
                        if attempt == 0:
                            print("🛑 Bloqueo detectado. Lanzando Auto-Cookie...")
                            success = get_cookies_interactively(url, auto_cookie_path)
                            if success:
                                cookie_path_to_use = str(auto_cookie_path)
                                continue
                            else:
                                raise Exception("🛑 YouTube/TikTok bloqueó la descarga (Requiere Sesión/Captcha) y la interfaz gráfica falló. Pega tu texto de cookies actualizado en el nodo de forma manual.")
                        else:
                            raise Exception(f"🛑 Error final de descarga:\n{error_msg[-200:]}")
                    else:
                        raise Exception(f"🛑 Error en yt-dlp:\n{error_msg[-200:]}")
                else:
                    raise e

NODE_CLASS_MAPPINGS = {"YTDLPVideoDownloader": YTDLPVideoDownloader}
NODE_DISPLAY_NAME_MAPPINGS = {"YTDLPVideoDownloader": "YT-DLP Downloader (Auto-Quality) 📥"}
