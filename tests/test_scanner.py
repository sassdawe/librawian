import unittest
from unittest.mock import Mock

from librawian.scanner import ScanSession, isbn13


class ISBNTests(unittest.TestCase):
    def test_bookland_checksums(self):
        for number in ("9780306406157", "9791090636071"):
            with self.subTest(number=number):
                self.assertEqual(isbn13(number), number)

    def test_rejects_non_books_and_malformed_barcodes(self):
        for value in ("", "0306406152", "9780306406158", "4006381333931",
                      "9790060115615", "９７８０３０６４０６１５７", "=9780306406157",
                      "978030640615X", "9780306406157\n"):
            with self.subTest(value=value):
                self.assertIsNone(isbn13(value))


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.session = ScanSession()
        self.write = Mock()

    def test_repeated_frames_write_once_even_after_empty_frames(self):
        self.assertEqual(self.session.accept(["9780306406157"], self.write), "9780306406157")
        self.session.accept([], self.write)
        self.assertIsNone(self.session.accept(["9780306406157"], self.write))
        self.write.assert_called_once_with("9780306406157")

    def test_next_book_and_explicit_repeat(self):
        self.session.accept(["9780306406157"], self.write)
        self.session.accept(["9791090636071"], self.write)
        self.session.last_isbn = None
        self.session.accept(["9791090636071"], self.write)
        self.assertEqual(self.write.call_count, 3)

    def test_ambiguous_or_invalid_frames_do_not_write(self):
        for values in ([], ["invalid"], ["9780306406157", "9791090636071"]):
            self.assertIsNone(self.session.accept(values, self.write))
        self.write.assert_not_called()

    def test_duplicate_detections_in_one_frame_are_unambiguous(self):
        self.session.accept(["9780306406157", "9780306406157", "invalid"], self.write)
        self.write.assert_called_once_with("9780306406157")

    def test_failed_write_can_be_retried(self):
        self.write.side_effect = RuntimeError("Excel is busy")
        with self.assertRaises(RuntimeError):
            self.session.accept(["9780306406157"], self.write)
        self.assertIsNone(self.session.last_isbn)
        self.write.side_effect = None
        self.session.accept(["9780306406157"], self.write)
        self.assertEqual(self.session.last_isbn, "9780306406157")
