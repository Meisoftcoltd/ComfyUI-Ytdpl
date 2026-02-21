
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add the parent directory to sys.path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))

# Import the module
import __init__ as my_module

class TestNewPathLogic(unittest.TestCase):
    def setUp(self):
        # Patch mkdir globally for the test duration
        self.mkdir_patcher = patch('pathlib.Path.mkdir')
        self.mock_mkdir = self.mkdir_patcher.start()

        # Patch exists
        self.exists_patcher = patch('pathlib.Path.exists')
        self.mock_exists = self.exists_patcher.start()
        self.mock_exists.return_value = True

        self.downloader = my_module.YTDLPVideoDownloader()

    def tearDown(self):
        self.mkdir_patcher.stop()
        self.exists_patcher.stop()

    @patch('subprocess.Popen')
    @patch('subprocess.run')
    @patch('subprocess.check_call')
    def test_download_uses_correct_path(self, mock_check_call, mock_run, mock_popen):
        # Setup mocks
        mock_run_return = MagicMock()
        mock_run_return.returncode = 0
        # simulate absolute path return from yt-dlp --get-filename
        expected_filename = "video.mp4"
        # Since we use -P, expected filename is full path or relative to -P?
        # In the code: expected_filename = filename_res.stdout...
        # If -P is absolute, it returns absolute.
        expected_path = self.downloader.output_dir / expected_filename
        mock_run_return.stdout = str(expected_path)
        mock_run.return_value = mock_run_return

        # Mock Popen
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = ["Download complete"]
        mock_process.wait.return_value = None
        mock_popen.return_value = mock_process

        # Inputs
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        cookies_file = "Ninguno"
        browser_source = "Ninguno"
        update_yt_dlp = False
        quality = "best"
        format_type = "mp4"

        # Call download_video
        result = self.downloader.download_video(
            url, "", cookies_file, browser_source, update_yt_dlp, quality, format_type
        )

        # Verify result
        self.assertEqual(result[0], str(expected_path))

        # Verify subprocess.run calls (get-filename)
        # It might be called multiple times if first fails, but here first succeeds.
        self.assertTrue(mock_run.called)

        # Verify arguments of run (get-filename)
        args_run, _ = mock_run.call_args
        cmd_run = args_run[0]
        self.assertIn("-P", cmd_run)
        p_index = cmd_run.index("-P")
        self.assertEqual(cmd_run[p_index+1], str(self.downloader.output_dir))

        # Verify subprocess.Popen calls (download)
        self.assertTrue(mock_popen.called)
        args_popen, _ = mock_popen.call_args
        cmd_popen = args_popen[0]

        # Verify -P argument exists and points to output/ytdpl
        self.assertIn("-P", cmd_popen)
        p_index_pop = cmd_popen.index("-P")
        self.assertEqual(cmd_popen[p_index_pop+1], str(self.downloader.output_dir))

        # Verify restrict-filenames is present
        self.assertIn("--restrict-filenames", cmd_popen)

if __name__ == '__main__':
    unittest.main()
