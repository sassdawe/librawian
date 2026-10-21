"""Write through the running Excel application, never through files on disk."""

import sys


class ExcelTarget:
    def __init__(self, selection):
        if selection is None or selection.count != 1:
            raise ValueError("Select exactly one ISBN cell in Excel, then connect again.")
        self.sheet = selection.sheet
        self.row = selection.row
        self.column = selection.column
        self.name = f"{self.sheet.book.name} / {self.sheet.name}"

    @classmethod
    def connect(cls):
        if sys.platform not in ("win32", "darwin"):
            raise RuntimeError("Live Excel requires Windows or macOS. Use Clipboard mode here.")
        import xlwings as xw

        if sys.platform == "win32":
            from xlwings import _xlwindows

            # xlwings otherwise retries rejected COM calls forever on the UI thread.
            _xlwindows.N_COM_ATTEMPTS = 1
        app = xw.apps.active
        if app is None or app.books.active is None:
            raise RuntimeError("Open your existing workbook in desktop Excel first.")
        return cls(app.selection)

    @property
    def cell(self):
        if self.row > 1_048_576:
            raise ValueError("The end of the worksheet has been reached. Select another cell.")
        return self.sheet.range((self.row, self.column))

    @property
    def description(self):
        return f"{self.name} / row {self.row}, column {self.column}"

    def write(self, number):
        cell = self.cell
        if cell.merge_cells:
            raise ValueError("Merged cells are not supported. Select an unmerged ISBN cell.")
        if cell.value is not None or cell.formula not in (None, ""):
            raise ValueError(f"{cell.address} is not empty. Nothing was overwritten; select another cell.")
        cell.number_format = "@"
        cell.value = number
        self.row += 1
