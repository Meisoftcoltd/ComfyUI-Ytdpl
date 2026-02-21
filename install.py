import os
import sys
import subprocess
import shutil

def install_python_requirements():
    requirements_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if os.path.exists(requirements_path):
        print(f"📥 [ComfyUI-Ytdpl] Installing requirements from {requirements_path}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", requirements_path])
            print("✅ [ComfyUI-Ytdpl] Successfully installed Python requirements.")
        except subprocess.CalledProcessError as e:
            print(f"❌ [ComfyUI-Ytdpl] Error installing Python requirements: {e}")
    else:
        print("⚠️ [ComfyUI-Ytdpl] No requirements.txt found.")

def install_system_dependencies():
    """Instala Deno si no se encuentra en el sistema (Requerido para JS Challenges de YouTube)"""
    if not shutil.which("deno"):
        print("⚙️ [ComfyUI-Ytdpl] Deno no encontrado. Instalando motor JS de Deno...")
        try:
            # Ejecuta el script oficial de instalación de Deno
            subprocess.check_call("curl -fsSL https://deno.land/install.sh | sh", shell=True)
            print("✅ [ComfyUI-Ytdpl] Deno instalado correctamente.")
        except Exception as e:
            print(f"❌ [ComfyUI-Ytdpl] Fallo al instalar Deno automáticamente: {e}")
            print("👉 SUGERENCIA: Es probable que el sistema no tenga 'unzip' instalado.")
            print("Abre tu terminal de WSL/Linux y ejecuta manualmente:")
            print("sudo apt update && sudo apt install unzip -y && curl -fsSL https://deno.land/install.sh | sh")
    else:
        print("✅ [ComfyUI-Ytdpl] Deno ya está instalado en el sistema.")

if __name__ == "__main__":
    print("🚀 Iniciando instalación de dependencias para ComfyUI-Ytdpl...")
    install_python_requirements()
    install_system_dependencies()
    print("🎉 Instalación finalizada.")