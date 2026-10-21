"""ISBN validation and repeat suppression, independent of camera hardware."""


def isbn13(value: str) -> str | None:
    """Accept only checksum-valid 978/979 Bookland EAN-13 barcodes."""
    if len(value) != 13 or not value.isascii() or not value.isdigit():
        return None
    if not value.startswith(("978", "979")) or value.startswith("9790"):
        return None
    total = sum(int(digit) * (1 if i % 2 == 0 else 3)
                for i, digit in enumerate(value))
    return value if total % 10 == 0 else None


class ScanSession:
    def __init__(self):
        self.last_isbn = None

    def accept(self, values, write):
        """Write one unambiguous ISBN; remember it only after a successful write."""
        valid = {number for value in values if (number := isbn13(value))}
        if len(valid) != 1:
            return None
        number = valid.pop()
        if number == self.last_isbn:
            return None
        write(number)
        self.last_isbn = number
        return number
