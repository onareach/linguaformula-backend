"""Validate guided-learning image captions (limited_inline: **/__ bold, */_ italic only)."""


class CaptionValidationError(Exception):
    """Raised when caption markup is invalid."""

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def validate_limited_inline_caption(caption: str) -> None:
    """
    Reject disallowed constructs; do not strip. Empty string is valid.
    """
    if caption is None:
        return
    if not isinstance(caption, str):
        raise CaptionValidationError("caption_invalid_type")
    if caption == "":
        return
    if "\n" in caption or "\r" in caption:
        raise CaptionValidationError("caption_multiline")
    if "<" in caption:
        raise CaptionValidationError("caption_raw_html")
    if "[" in caption or "]" in caption:
        raise CaptionValidationError("caption_links_disallowed")
    if "`" in caption:
        raise CaptionValidationError("caption_code_disallowed")
    n = len(caption)
    i = _consume_document(caption, 0, n)
    if i != n:
        raise CaptionValidationError("caption_invalid_markup")


def _consume_bold_ds(s: str, i: int, end: int) -> int:
    while i < end:
        if i + 1 < end and s[i : i + 2] == "**":
            return i + 2
        if i + 1 < end and s[i : i + 2] == "__":
            i = _consume_bold_du(s, i + 2, end)
        elif s[i] == "*":
            if i + 1 < end and s[i + 1] == "*":
                raise CaptionValidationError("caption_invalid_markup")
            i = _consume_italic_star(s, i + 1, end)
        elif s[i] == "_":
            if i + 1 < end and s[i + 1] == "_":
                i = _consume_bold_du(s, i + 2, end)
            else:
                i = _consume_italic_us(s, i + 1, end)
        else:
            i += 1
    raise CaptionValidationError("caption_unclosed_delimiter")


def _consume_bold_du(s: str, i: int, end: int) -> int:
    while i < end:
        if i + 1 < end and s[i : i + 2] == "__":
            return i + 2
        if i + 1 < end and s[i : i + 2] == "**":
            i = _consume_bold_ds(s, i + 2, end)
        elif s[i] == "*":
            if i + 1 < end and s[i + 1] == "*":
                i = _consume_bold_ds(s, i + 2, end)
            else:
                i = _consume_italic_star(s, i + 1, end)
        elif s[i] == "_":
            if i + 1 < end and s[i + 1] == "_":
                raise CaptionValidationError("caption_invalid_markup")
            i = _consume_italic_us(s, i + 1, end)
        else:
            i += 1
    raise CaptionValidationError("caption_unclosed_delimiter")


def _consume_italic_star(s: str, i: int, end: int) -> int:
    while i < end:
        if i + 1 < end and s[i : i + 2] == "**":
            i = _consume_bold_ds(s, i + 2, end)
        elif i + 1 < end and s[i : i + 2] == "__":
            i = _consume_bold_du(s, i + 2, end)
        elif s[i] == "*":
            if i + 1 < end and s[i + 1] == "*":
                raise CaptionValidationError("caption_invalid_markup")
            return i + 1
        elif s[i] == "_":
            if i + 1 < end and s[i + 1] == "_":
                i = _consume_bold_du(s, i + 2, end)
            else:
                i = _consume_italic_us(s, i + 1, end)
        else:
            i += 1
    raise CaptionValidationError("caption_unclosed_delimiter")


def _consume_italic_us(s: str, i: int, end: int) -> int:
    while i < end:
        if i + 1 < end and s[i : i + 2] == "**":
            i = _consume_bold_ds(s, i + 2, end)
        elif i + 1 < end and s[i : i + 2] == "__":
            i = _consume_bold_du(s, i + 2, end)
        elif s[i] == "_":
            if i + 1 < end and s[i + 1] == "_":
                raise CaptionValidationError("caption_invalid_markup")
            return i + 1
        elif s[i] == "*":
            if i + 1 < end and s[i + 1] == "*":
                i = _consume_bold_ds(s, i + 2, end)
            else:
                i = _consume_italic_star(s, i + 1, end)
        else:
            i += 1
    raise CaptionValidationError("caption_unclosed_delimiter")


def _consume_document(s: str, i: int, end: int) -> int:
    while i < end:
        if i + 1 < end and s[i : i + 2] == "**":
            i = _consume_bold_ds(s, i + 2, end)
        elif i + 1 < end and s[i : i + 2] == "__":
            i = _consume_bold_du(s, i + 2, end)
        elif s[i] == "*":
            if i + 1 < end and s[i + 1] == "*":
                raise CaptionValidationError("caption_invalid_markup")
            i = _consume_italic_star(s, i + 1, end)
        elif s[i] == "_":
            if i + 1 < end and s[i + 1] == "_":
                i = _consume_bold_du(s, i + 2, end)
            else:
                i = _consume_italic_us(s, i + 1, end)
        else:
            i += 1
    return i
