import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add parent directory to path to import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock subprocess.check_call to avoid actual installation during import if needed
with patch("subprocess.check_call"):
    from __init__ import YTDLPVideoDownloader

class TestErrorHandling(unittest.TestCase):
    def setUp(self):
        # Patch __init__ to avoid directory creation issues
        with patch.object(YTDLPVideoDownloader, '__init__', lambda self: None):
            self.downloader = YTDLPVideoDownloader()
            # Manually set attributes that __init__ would have set
            self.downloader.base_input_path = Path("./input")
            self.downloader.cookies_dir = self.downloader.base_input_path / "cookies"

    @patch("subprocess.run")
    @patch("webbrowser.open")
    def test_captcha_detection(self, mock_webbrowser, mock_subprocess):
        # Setup mock to fail with a captcha error in stderr
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: Sign in to confirm you are not a bot. Verify here."
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        # We need to ensure dest_path.mkdir works or is mocked.
        # In download_video: dest_path.mkdir(parents=True, exist_ok=True)
        # We can mock Path.mkdir but that's global.
        # Or we can just ensure the path exists in our test env.
        # or mock pathlib.Path.mkdir

        with patch("pathlib.Path.mkdir"):
             # Call download_video
            try:
                self.downloader.download_video(
                    url="http://example.com",
                    cookies_file="Ninguno",
                    update_yt_dlp=False,
                    output_dir="input",
                    filename_template="test",
                    quality="best",
                    format="mp4"
                )
            except Exception as e:
                self.assertIn("TikTok/YouTube pide Captcha", str(e))
                self.assertTrue(mock_webbrowser.called)
                return

        self.fail("Should have raised Exception")

    @patch("subprocess.run")
    @patch("webbrowser.open")
    def test_generic_error(self, mock_webbrowser, mock_subprocess):
        # Setup mock to fail with a generic error
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "ERROR: Video unavailable"
        mock_result.stdout = ""
        mock_subprocess.return_value = mock_result

        with patch("pathlib.Path.mkdir"):
            # Call download_video
            try:
                self.downloader.download_video(
                    url="http://example.com",
                    cookies_file="Ninguno",
                    update_yt_dlp=False,
                    output_dir="input",
                    filename_template="test",
                    quality="best",
                    format="mp4"
                )
            except Exception as e:
                self.assertIn("Error al obtener información del video", str(e))
                self.assertFalse(mock_webbrowser.called)
                return

        self.fail("Should have raised Exception")

if __name__ == "__main__":
    unittest.main()
