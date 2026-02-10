import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure the root directory is in sys.path so we can import __init__.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock subprocess to prevent import side effects
mock_subprocess = MagicMock()
sys.modules['subprocess'] = mock_subprocess

import __init__ as comfy_node

# Mock initialization to avoid filesystem access
def mock_init_downloader(self):
    self.base_input_path = MagicMock()
    self.base_input_path.resolve.return_value = self.base_input_path
    self.base_input_path.__truediv__.return_value = self.base_input_path
    self.cookies_dir = MagicMock()
    self.cookies_dir.__truediv__.return_value = self.cookies_dir

class TestBrowserSelection(unittest.TestCase):
    def setUp(self):
        self.original_init = comfy_node.YTDLPVideoDownloader.__init__
        comfy_node.YTDLPVideoDownloader.__init__ = mock_init_downloader

    def tearDown(self):
        comfy_node.YTDLPVideoDownloader.__init__ = self.original_init

    @patch('__init__.subprocess.run')
    def test_impersonate_chrome(self, mock_run):
        downloader = comfy_node.YTDLPVideoDownloader()

        # Mocks for subprocess calls
        mock_res_filename = MagicMock()
        mock_res_filename.returncode = 0
        mock_res_filename.stdout = "test.mp4"

        mock_res_download = MagicMock()
        mock_res_download.returncode = 0

        mock_run.side_effect = [mock_res_filename, mock_res_download]

        try:
             downloader.download_video(
                url="http://example.com",
                cookies_file="Ninguno",
                browser_source="Chrome",
                update_yt_dlp=False,
                output_dir="input",
                filename_template="%(title)s.%(ext)s",
                quality="best",
                format="mp4"
            )
        except Exception:
            pass

        found = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if "--impersonate" in args and "chrome-110" in args:
                found = True
                break
        self.assertTrue(found)

    @patch('__init__.subprocess.run')
    def test_impersonate_firefox(self, mock_run):
        downloader = comfy_node.YTDLPVideoDownloader()

        mock_res_filename = MagicMock()
        mock_res_filename.returncode = 0
        mock_res_filename.stdout = "test.mp4"

        mock_res_download = MagicMock()
        mock_res_download.returncode = 0

        mock_run.side_effect = [mock_res_filename, mock_res_download]

        try:
             downloader.download_video(
                url="http://example.com",
                cookies_file="Ninguno",
                browser_source="Firefox",
                update_yt_dlp=False,
                output_dir="input",
                filename_template="%(title)s.%(ext)s",
                quality="best",
                format="mp4"
            )
        except Exception:
            pass

        found = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if "--impersonate" in args and "firefox-133" in args:
                found = True
                break
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
