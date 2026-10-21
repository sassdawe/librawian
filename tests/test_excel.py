import unittest
from unittest.mock import Mock, PropertyMock, patch

from librawian.excel import ExcelTarget
from librawian.scanner import ScanSession


class ExcelTests(unittest.TestCase):
    def setUp(self):
        self.selection = Mock(count=1, row=5, column=3)
        self.cell = Mock(value=None, formula="", merge_cells=False)
        self.selection.sheet.range.return_value = self.cell
        self.target = ExcelTarget(self.selection)

    def test_writes_text_to_selected_column_then_moves_down(self):
        self.target.write("9780306406157")
        self.selection.sheet.range.assert_called_once_with((5, 3))
        self.assertEqual(self.cell.number_format, "@")
        self.assertEqual(self.cell.value, "9780306406157")
        self.assertEqual(self.target.row, 6)
        self.assertEqual(self.target.column, 3)
        self.selection.sheet.book.save.assert_not_called()

    def test_refuses_existing_values_including_zero_and_empty_text(self):
        for value in ("existing details", 0, ""):
            with self.subTest(value=value):
                self.cell.value = value
                with self.assertRaisesRegex(ValueError, "not empty"):
                    self.target.write("9780306406157")
                self.assertEqual(self.cell.value, value)
                self.assertEqual(self.target.row, 5)

    def test_refuses_formula_even_if_result_is_empty(self):
        self.cell.formula = '=IF(A1="", "", A1)'
        with self.assertRaisesRegex(ValueError, "not empty"):
            self.target.write("9780306406157")
        self.assertIsNone(self.cell.value)
        self.assertEqual(self.target.row, 5)

    def test_refuses_merged_cells(self):
        self.cell.merge_cells = True
        with self.assertRaisesRegex(ValueError, "Merged"):
            self.target.write("9780306406157")
        self.assertEqual(self.target.row, 5)

    def test_refuses_multiple_cells_or_missing_selection(self):
        for selection in (None, Mock(count=2)):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                ExcelTarget(selection)

    def test_write_failure_does_not_advance_row(self):
        type(self.cell).value = PropertyMock(side_effect=RuntimeError("Workbook closed"))
        with self.assertRaises(RuntimeError):
            self.target.write("9780306406157")
        self.assertEqual(self.target.row, 5)

    def test_scan_to_excel_preserves_existing_book_details(self):
        session = ScanSession()
        session.accept(["9780306406157"], self.target.write)
        session.accept(["9780306406157"], self.target.write)
        self.cell.value = "Already catalogued"
        with self.assertRaises(ValueError):
            session.accept(["9791090636071"], self.target.write)
        self.assertEqual(self.cell.value, "Already catalogued")
        self.assertEqual(self.target.row, 6)
        self.assertEqual(session.last_isbn, "9780306406157")

    def test_end_of_worksheet_does_not_wrap(self):
        self.target.row = 1_048_577
        with self.assertRaisesRegex(ValueError, "end of the worksheet"):
            self.target.write("9780306406157")
        self.selection.sheet.range.assert_not_called()

    @patch("librawian.excel.sys.platform", "linux")
    def test_unsupported_live_excel_has_clear_fallback(self):
        with self.assertRaisesRegex(RuntimeError, "Clipboard"):
            ExcelTarget.connect()

    @patch("librawian.excel.sys.platform", "win32")
    def test_connect_only_attaches_to_running_excel(self):
        xw = Mock()
        xw.apps.active.selection = self.selection
        with patch.dict("sys.modules", {"xlwings": xw}):
            self.assertEqual(ExcelTarget.connect().row, 5)
            xw.App.assert_not_called()
            xw.Book.assert_not_called()

    @patch("librawian.excel.sys.platform", "win32")
    def test_no_running_excel_is_actionable(self):
        xw = Mock()
        xw.apps.active = None
        with patch.dict("sys.modules", {"xlwings": xw}):
            with self.assertRaisesRegex(RuntimeError, "Open your existing workbook"):
                ExcelTarget.connect()
