
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add the parent directory to sys.path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))

# Import the module
import __init__ as my_module

class TestPathTraversal(unittest.TestCase):
    def setUp(self):
        # Patch mkdir globally for the test duration to avoid PermissionError
        self.mkdir_patcher = patch('pathlib.Path.mkdir')
        self.mock_mkdir = self.mkdir_patcher.start()
        self.downloader = my_module.YTDLPVideoDownloader()

    def tearDown(self):
        self.mkdir_patcher.stop()

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    def test_absolute_path_exploit(self, mock_check_call, mock_run):
        # Inputs
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cookies_file = "Ninguno"
        update_yt_dlp = False
        output_dir = "input"
        filename_template = "/tmp/pwned.mp4" # Malicious input: absolute path
        quality = "best"
        format_type = "mp4"

        with self.assertRaises(Exception) as cm:
            self.downloader.download_video(
                url, cookies_file, update_yt_dlp, output_dir, filename_template, quality, format_type
            )

        self.assertIn("Error de Seguridad", str(cm.exception))
        # Spanish: "filename_template no puede ser una ruta absoluta"
        self.assertIn("filename_template no puede ser una ruta absoluta", str(cm.exception))

        # Verify subprocess was NOT called
        mock_run.assert_not_called()

    @patch('subprocess.run')
    @patch('subprocess.check_call')
    def test_traversal_exploit(self, mock_check_call, mock_run):
        # Inputs
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cookies_file = "Ninguno"
        update_yt_dlp = False
        output_dir = "input"
        filename_template = "../pwned.mp4" # Malicious input: traversal
        quality = "best"
        format_type = "mp4"

        with self.assertRaises(Exception) as cm:
            self.downloader.download_video(
                url, cookies_file, update_yt_dlp, output_dir, filename_template, quality, format_type
            )

        self.assertIn("Error de Seguridad", str(cm.exception))
        self.assertIn("filename_template intenta salir del directorio de destino", str(cm.exception))

        # Verify subprocess was NOT called
        mock_run.assert_not_called()

    @patch('pathlib.Path.exists')
    @patch('subprocess.run')
    @patch('subprocess.check_call')
    def test_valid_paths(self, mock_check_call, mock_run, mock_exists):
        # Setup mocks
        mock_run_return = MagicMock()
        mock_run_return.returncode = 0
        mock_run_return.stdout = "some_video.mp4"
        mock_run.return_value = mock_run_return

        # Make exists return True so it finds the "downloaded" file
        mock_exists.return_value = True

        # Inputs
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cookies_file = "Ninguno"
        update_yt_dlp = False
        output_dir = "input"
        quality = "best"
        format_type = "mp4"

        # Case 1: Simple filename
        self.downloader.download_video(
            url, cookies_file, update_yt_dlp, output_dir, "video.mp4", quality, format_type
        )
        # Should succeed and call subprocess

        # Case 2: Subdirectory
        self.downloader.download_video(
            url, cookies_file, update_yt_dlp, output_dir, "sub/video.mp4", quality, format_type
        )

        # Case 3: Dots in filename but no traversal
        self.downloader.download_video(
            url, cookies_file, update_yt_dlp, output_dir, "my..video.mp4", quality, format_type
        )

        # Check call count - we called it 3 times, each triggers 2 calls (get-filename + download)
        # unless cached or something, but here we don't mock internal caching if any.
        # Actually logic is:
        # 1. get-filename (subprocess.run)
        # 2. download (subprocess.run)
        # So 2 calls per invocation = 6 calls total.

        self.assertEqual(mock_run.call_count, 6)


if __name__ == '__main__':
    unittest.main()
