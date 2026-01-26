# ComfyUI-Ytdpl

Nodo de ComfyUI para descargar videos y audio utilizando `yt-dlp` con selección automática de calidad y soporte para cookies.

## Características
- **Descarga Inteligente:** Soporte para una amplia variedad de sitios web compatibles con `yt-dlp`.
- **Gestión de Calidad:** Selección de calidad (best, 1080p, 720p, etc.) con reintento automático en calidad superior si la elegida no está disponible.
- **Formatos Versátiles:** Soporta múltiples formatos de video (mp4, mkv, webm, etc.) y audio (mp3, wav, flac, etc.).
- **Soporte de Cookies:** Permite usar cookies para acceder a contenido privado o evitar bloqueos y captchas.
- **Actualización Automática:** Opción para mantener `yt-dlp` actualizado a la última versión automáticamente.

## Instalación

1. Navega a la carpeta de nodos personalizados de tu instalación de ComfyUI:
   ```bash
   cd ComfyUI/custom_nodes
   ```
2. Clona este repositorio:
   ```bash
   git clone https://github.com/tu-usuario/ComfyUI-Ytdpl.git
   ```
3. Instala las dependencias necesarias:
   ```bash
   pip install -r requirements.txt
   ```

## Configuración y Uso de Cookies

Las cookies son fundamentales para descargar contenido que requiere autenticación o para sortear medidas de seguridad de plataformas como YouTube o TikTok.

### ¿Dónde colocar las cookies?
El nodo busca archivos de cookies en una carpeta específica dentro de tu instalación de ComfyUI:

`ComfyUI/input/cookies/`

*Nota: El nodo creará esta carpeta automáticamente la primera vez que se ejecute si no existe.*

Simplemente coloca tus archivos `.txt` en esa carpeta. En la interfaz de ComfyUI, podrás seleccionar el archivo deseado en el parámetro `cookies_file`.

### Cómo exportar cookies desde navegadores Chromium (Chrome, Edge, Brave, etc.)
Para que `yt-dlp` reconozca las cookies, estas deben estar en formato **Netscape**. Sigue estos pasos para obtenerlas:

1. **Instalar una extensión:**
   - Busca en la Chrome Web Store una extensión como **"Get cookies.txt LOCALLY"** o **"EditThisCookie"**.
2. **Obtener las cookies:**
   - Ve al sitio web del que deseas descargar (ej. youtube.com).
   - Asegúrate de haber iniciado sesión si el contenido es privado.
   - Haz clic en la extensión y selecciona **Exportar** (asegúrate de que el formato sea Netscape/Cookies.txt).
3. **Guardar y mover:**
   - Guarda el archivo con un nombre descriptivo, por ejemplo: `youtube.txt`.
   - Mueve este archivo a `ComfyUI/input/cookies/`.

## Parámetros del Nodo

- **url**: El enlace del video o audio.
- **cookies_file**: Menú desplegable para elegir uno de los archivos en `input/cookies/`. Selecciona "Ninguno" si no deseas usar cookies.
- **force_update**: Si está activado, el nodo ejecutará `pip install -U yt-dlp` antes de comenzar la descarga para asegurar la máxima compatibilidad.
- **output_dir**: Directorio donde se guardará el archivo. Por defecto es la carpeta `input` de ComfyUI.
- **filename_template**: Estructura del nombre del archivo final.
- **quality**: Calidad preferida. Si la calidad elegida falla, el nodo intentará descargar la mejor calidad disponible ("best").
- **format**: Extensión del archivo final (video o audio).

## Solución de Problemas

- **Error de Captcha/403 Forbidden:** Esto ocurre frecuentemente con TikTok o YouTube. Asegúrate de estar usando cookies actualizadas y que el paquete `curl-cffi` esté instalado correctamente.
- **Archivo no encontrado:** Verifica que el `output_dir` sea válido y que tengas permisos de escritura.
