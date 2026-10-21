# librawian

Scan book barcodes with a webcam and put ISBNs into your **already-open Excel
workbook**, alongside the book details you have captured. No online lookup or
upload is involved.

## Install and run

Requires Python 3.10+ with Tk, a webcam, and (for live insertion) desktop Microsoft
Excel. Excel Online is not supported.

**Windows (first supported platform):** install Python from python.org, including
Tcl/Tk and pip. In PowerShell, from your downloaded checkout:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\python -m librawian
```

If the barcode decoder reports a missing DLL, install the Microsoft Visual C++
2013 Redistributable (x64 for 64-bit Python, x86 for 32-bit Python), required by
pyzbar's bundled Windows ZBar DLLs. Enable desktop camera access in Windows
Settings → Privacy & security → Camera.

**macOS:** install Python with Tk support (the python.org installer includes Tk),
desktop Excel, and ZBar (`brew install zbar`). Then:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m librawian
```

Allow camera access and automation of Microsoft Excel when macOS prompts.
On Apple Silicon, use a native Python and matching Homebrew installation.

**Linux:** the scanner and clipboard mode work; live Excel automation is
Windows/macOS only. On Debian/Ubuntu install `python3-venv python3-tk libzbar0`
with apt, then use the macOS Python commands above. Paste into your spreadsheet
manually with Ctrl+V. Keep Librawian open while using its clipboard.

The installation also provides a `librawian` desktop command in the virtual
environment's scripts directory. No Excel add-in is required.

## Scan into your existing book list

1. Open your workbook in desktop Excel. Select **one empty ISBN cell** next to
   the first book's existing details.
2. Launch Librawian, select **Excel**, and click **Use selected Excel cell**.
   Check the displayed workbook, sheet, row, and column before starting.
   If several Excel instances are running, close the others to avoid ambiguity.
3. Click **Start** (camera index `0` is the default; try `1` for another camera).
   Hold a single book's **978/979 EAN-13 barcode** clearly in view with good
   lighting. The preview and status show progress; a successful scan beeps.
4. Each valid new ISBN is written as text, then the destination moves down one
   row in the **same column and worksheet**. Scan books in the same order as
   your existing rows. Changing Excel's selection does not redirect scanning.
5. Click **Stop** before changing destination, sorting, filtering, or editing the
   list. Select another cell and reconnect to skip a populated row or correct
   alignment. **Save the workbook yourself in Excel** when finished.

Existing values, formulas (even those displaying blank), and merged cells are
never overwritten. A write/camera error stops scanning and shows the reason;
the destination row advances only after a successful write. A closed, busy,
read-only, or protected workbook may require fixing the problem and reconnecting.
Use an unfiltered, unmerged ISBN column, with one existing book per row.

Repeated frames of the same ISBN are ignored, including after Stop/Start.
For consecutive copies of the same edition, click **Allow same ISBN again**
only when ready to fill the next row. Multiple distinct book barcodes in one
frame are ignored; show just one. Retail barcodes, invalid checksums, ISBN-10
text, and 9790 music identifiers are not accepted.

**Clipboard mode** is available on every platform: each new ISBN replaces the
clipboard, without writing to Excel or advancing a spreadsheet selection.
Paste each scan before showing the next book. The last ISBN is also displayed
in a selectable text field.

## Development checks

After installing the app, run the built-in unittest suite:

```sh
python -m unittest discover -s tests -v
```

Core and Excel-adapter tests use no camera or Excel installation. UI tests
require Tk and a display (or `xvfb-run` on Linux). Actual camera capture and
live Excel insertion must also be checked on the target Windows/macOS machine.
