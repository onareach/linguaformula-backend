import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from limited_inline_caption import CaptionValidationError, validate_limited_inline_caption


class TestLimitedInlineCaption(unittest.TestCase):
    def test_empty_ok(self):
        validate_limited_inline_caption("")
        validate_limited_inline_caption("plain")

    def test_bold_star(self):
        validate_limited_inline_caption("a **b** c")
        validate_limited_inline_caption("**x**")

    def test_bold_under(self):
        validate_limited_inline_caption("__z__")

    def test_italic(self):
        validate_limited_inline_caption("*a*")
        validate_limited_inline_caption("_b_")
        validate_limited_inline_caption("a*b*c")

    def test_nested(self):
        validate_limited_inline_caption("*a **b** c*")
        validate_limited_inline_caption("**a *b* c**")

    def test_reject_unmatched_star(self):
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("*open")
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("close*")

    def test_reject_unmatched_bold(self):
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("**only")

    def test_reject_newline(self):
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("a\nb")

    def test_reject_bracket_link(self):
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("[t](u)")

    def test_reject_html(self):
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("a<b>")

    def test_reject_backtick(self):
        with self.assertRaises(CaptionValidationError):
            validate_limited_inline_caption("`x`")


if __name__ == "__main__":
    unittest.main()
