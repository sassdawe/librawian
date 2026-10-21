import tkinter as tk
import unittest
from unittest.mock import Mock, patch

import numpy as np

from librawian.app import ScannerApp
from librawian.excel import ExcelTarget


def book_frame():
    # EAN-13 bars for 9780306406157, with quiet zones at both ends.
    bars = (
        "10101110110001001010011101111010100111010111101010"
        "101110011100101010000110011010011101000100101"
    )
    pixels = [255] * 12 + [0 if bit == "1" else 255 for bit in bars] + [255] * 12
    line = np.repeat(np.array(pixels, dtype=np.uint8), 4)
    return np.tile(line[None, :, None], (180, 1, 3))


class AppTests(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("Tk requires a display; use xvfb-run on Linux.")
        self.root.withdraw()
        self.app = ScannerApp(self.root)
        self.app.mode.set("Clipboard")
        self.camera = Mock()
        self.camera.isOpened.return_value = True
        self.camera.read.return_value = (True, book_frame())
        self.capture = patch("cv2.VideoCapture", return_value=self.camera).start()
        self.error = patch("librawian.app.messagebox.showerror").start()
        self.addCleanup(patch.stopall)

    def tearDown(self):
        if hasattr(self, "app"):
            self.app.close()

    def test_real_decoder_preview_and_clipboard(self):
        self.app.start()
        self.error.assert_not_called()
        self.assertEqual(self.app.latest.get(), "9780306406157")
        self.assertEqual(self.root.clipboard_get(), "9780306406157")
        self.assertGreater(self.app.preview.image.width(), 0)
        self.assertEqual(str(self.app.mode_picker["state"]), "disabled")
        self.app.stop()
        self.camera.release.assert_called_once()
        self.assertIsNone(self.app.pending)
        self.assertEqual(str(self.app.mode_picker["state"]), "readonly")

    def test_repeat_is_suppressed_across_restart_but_can_be_enabled(self):
        with patch.object(self.app, "send", wraps=self.app.send) as send:
            self.app.start()
            self.app.stop()
            self.app.start()
            self.app.stop()
            send.assert_called_once_with("9780306406157")
            self.app.allow_repeat()
            self.app.start()
            self.assertEqual(send.call_count, 2)

    def test_camera_to_excel_pipeline_writes_only_isbn_cell(self):
        selection = Mock(count=1, row=7, column=4)
        cell = Mock(value=None, formula="", merge_cells=False)
        selection.sheet.range.return_value = cell
        self.app.target = ExcelTarget(selection)
        self.app.mode.set("Excel")
        self.app.start()
        self.error.assert_not_called()
        selection.sheet.range.assert_called_once_with((7, 4))
        self.assertEqual(cell.value, "9780306406157")
        self.assertEqual(cell.number_format, "@")
        self.assertEqual(self.app.target.row, 8)

    def test_write_error_stops_camera_without_remembering_isbn(self):
        self.app.mode.set("Excel")
        self.app.target = Mock()
        self.app.target.write.side_effect = RuntimeError("Excel is busy")
        self.app.start()
        self.camera.release.assert_called_once()
        self.assertIsNone(self.app.camera)
        self.assertIsNone(self.app.pending)
        self.assertIsNone(self.app.session.last_isbn)
        self.assertIn("Excel is busy", self.app.status.get())
        self.error.assert_called_once()

    def test_camera_disconnect_stops_cleanly(self):
        self.camera.read.return_value = (False, None)
        self.app.start()
        self.assertIsNone(self.app.camera)
        self.camera.release.assert_called_once()
        self.assertIn("webcam", self.app.status.get())
        self.error.assert_called_once()

    def test_unavailable_camera_is_released(self):
        self.camera.isOpened.return_value = False
        self.app.start()
        self.camera.release.assert_called_once()
        self.assertIsNone(self.app.camera)
        self.error.assert_called_once()

    def test_excel_requires_explicit_destination(self):
        self.app.mode.set("Excel")
        self.app.start()
        self.capture.assert_not_called()
        self.error.assert_called_once()

    def test_failed_reconnect_clears_old_destination(self):
        self.app.target = Mock()
        with patch.object(ExcelTarget, "connect", side_effect=RuntimeError("Workbook closed")):
            self.app.connect()
        self.assertIsNone(self.app.target)
        self.assertIn("Not connected", self.app.destination.get())
        self.error.assert_called_once()
