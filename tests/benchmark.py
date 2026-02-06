
import sys
import os
import time
import unittest.mock
from pathlib import Path

# Add parent directory to sys.path to import __init__.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock subprocess to avoid actual side effects during import and execution
with unittest.mock.patch('subprocess.check_call') as mock_check_call, \
     unittest.mock.patch('subprocess.run') as mock_run:

    # Configure mock_run to return success for yt-dlp calls
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = "expected_filename.mp4\n"
    mock_run.return_value.stderr = ""

    # Import the module under test
    import __init__ as comfy_ytdlp

# Patch the __init__ method to use a local directory for testing
def mocked_init(self):
    self.base_input_path = Path("tests/input")
    self.cookies_dir = self.base_input_path / "cookies"
    self.cookies_dir.mkdir(parents=True, exist_ok=True)

comfy_ytdlp.YTDLPVideoDownloader.__init__ = mocked_init

def benchmark():
    downloader = comfy_ytdlp.YTDLPVideoDownloader()

    # Mock parameters
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    cookies_file = "Ninguno"
    update_yt_dlp = False
    output_dir = "input"
    filename_template = "%(title)s.%(ext)s"
    quality = "best"
    format_type = "mp4"

    # Pre-create the expected file so the download success check passes
    expected_file = Path("tests/input/expected_filename.mp4")
    expected_file.touch()

    # We need to mock subprocess again inside the function because the context manager above ended
    # Or we can wrap the whole execution

    iterations = 10000
    start_total = time.time_ns()

    with unittest.mock.patch('subprocess.check_call') as mock_check_call, \
         unittest.mock.patch('subprocess.run') as mock_run:

        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = str(expected_file.resolve()) + "\n"
        mock_run.return_value.stderr = ""

        # We also need to mock Path.exists if necessary, but since we created the file, it might work?
        # The code does: expected_path = Path(expected_filename)
        # expected_filename comes from mock_run.stdout.
        # So we should ensure stdout returns a path that exists.

        for _ in range(iterations):
            try:
                downloader.download_video(
                    url, cookies_file, update_yt_dlp, output_dir,
                    filename_template, quality, format_type
                )
            except Exception as e:
                print(f"Error during benchmark: {e}")
                import traceback
                traceback.print_exc()
                break

    end_total = time.time_ns()

    avg_time_ns = (end_total - start_total) / iterations
    print(f"Average execution time over {iterations} runs: {avg_time_ns:.2f} ns")
    print(f"Total time: {(end_total - start_total) / 1e9:.4f} s")

    # Clean up
    if expected_file.exists():
        expected_file.unlink()
    # clean up dir
    import shutil
    shutil.rmtree("tests/input")

if __name__ == "__main__":
    benchmark()
