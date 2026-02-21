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
    self.output_dir = MagicMock()
    self.output_dir.__truediv__.return_value = self.output_dir

class TestBrowserSelection(unittest.TestCase):
    def setUp(self):
        self.original_init = comfy_node.YTDLPVideoDownloader.__init__
        comfy_node.YTDLPVideoDownloader.__init__ = mock_init_downloader

    def tearDown(self):
        comfy_node.YTDLPVideoDownloader.__init__ = self.original_init

    @patch('__init__.subprocess.Popen')
    @patch('__init__.subprocess.run')
    def test_impersonate_chrome(self, mock_run, mock_popen):
        downloader = comfy_node.YTDLPVideoDownloader()

        # Mock get-filename (subprocess.run)
        mock_res_filename = MagicMock()
        mock_res_filename.returncode = 0
        mock_res_filename.stdout = "test.mp4"
        mock_run.return_value = mock_res_filename

        # Mock download (subprocess.Popen)
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ["Download complete"]
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        try:
             downloader.download_video(
                url="http://example.com",
                cookies_text="",
                cookies_file="Ninguno",
                browser_source="Chrome",
                update_yt_dlp=False,
                quality="best",
                format="mp4"
            )
        except Exception as e:
            # If exception is raised, print it to debug
            print(f"Exception raised: {e}")
            pass

        found = False
        # Check both run (get-filename) and popen (download) args
        for call in mock_run.call_args_list:
            args = call[0][0]
            if "--impersonate" in args and "chrome" in args:
                found = True
                break

        if not found:
             for call in mock_popen.call_args_list:
                args = call[0][0]
                if "--impersonate" in args and "chrome" in args:
                    found = True
                    break

        self.assertTrue(found)

    @patch('__init__.subprocess.Popen')
    @patch('__init__.subprocess.run')
    def test_impersonate_firefox(self, mock_run, mock_popen):
        downloader = comfy_node.YTDLPVideoDownloader()

        mock_res_filename = MagicMock()
        mock_res_filename.returncode = 0
        mock_res_filename.stdout = "test.mp4"
        mock_run.return_value = mock_res_filename

        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ["Download complete"]
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        try:
             downloader.download_video(
                url="http://example.com",
                cookies_text="",
                cookies_file="Ninguno",
                browser_source="Firefox",
                update_yt_dlp=False,
                quality="best",
                format="mp4"
            )
        except Exception:
            pass

        found = False
        for call in mock_run.call_args_list:
            args = call[0][0]
            if "--impersonate" in args and "firefox" in args:
                found = True
                break

        if not found:
             for call in mock_popen.call_args_list:
                args = call[0][0]
                if "--impersonate" in args and "firefox" in args:
                    found = True
                    break

        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
