"""Validation helpers for tbl_lesson_block (image / paragraph / formula)."""

from __future__ import annotations

from typing import Any, Optional, Tuple

from limited_inline_caption import CaptionValidationError, validate_limited_inline_caption

ALT_MAX = 500
CAPTION_MAX = 500
IMAGE_SCHEMA_VERSION = 1

ALIGN_VALUES = frozenset({"left", "center", "right"})
SIZE_PRESETS = frozenset({"inline", "medium", "large", "full"})


def _json_dict(content: Any) -> Optional[dict]:
    if content is None:
        return None
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        import json

        try:
            o = json.loads(content)
            return o if isinstance(o, dict) else None
        except Exception:
            return None
    return None


def validate_image_block_content(block_content: Any) -> Tuple[Optional[dict], Optional[str]]:
    """
    Returns (normalized dict, error_code) — one of them is always set.
    """
    bc = _json_dict(block_content)
    if bc is None:
        return None, "block_content_invalid"

    ver = bc.get("schema_version")
    if ver != IMAGE_SCHEMA_VERSION:
        return None, "image_schema_version_invalid"

    alt_text = bc.get("alt_text")
    if not isinstance(alt_text, str):
        return None, "alt_text_invalid"
    if len(alt_text) > ALT_MAX:
        return None, "alt_text_too_long"

    is_dec = bc.get("is_decorative")
    if not isinstance(is_dec, bool):
        return None, "is_decorative_invalid"

    if not is_dec and not alt_text.strip():
        return None, "alt_text_required_when_not_decorative"

    align = bc.get("align")
    if not isinstance(align, str) or align not in ALIGN_VALUES:
        return None, "align_invalid"

    size_preset = bc.get("size_preset")
    if not isinstance(size_preset, str) or size_preset not in SIZE_PRESETS:
        return None, "size_preset_invalid"

    caption = bc.get("caption", "")
    if caption is None:
        caption = ""
    if not isinstance(caption, str):
        return None, "caption_invalid"
    if len(caption) > CAPTION_MAX:
        return None, "caption_too_long"

    caption_format = bc.get("caption_format")
    if caption.strip():
        if caption_format is not None and caption_format != "limited_inline":
            return None, "caption_format_invalid"
        try:
            validate_limited_inline_caption(caption)
        except CaptionValidationError as e:
            return None, e.code
    elif caption_format is not None and caption_format != "limited_inline":
        return None, "caption_format_invalid"

    allowed = {
        "schema_version",
        "alt_text",
        "is_decorative",
        "align",
        "size_preset",
        "caption",
        "caption_format",
    }
    extra = set(bc.keys()) - allowed
    if extra:
        return None, "block_content_unknown_keys"

    out = {
        "schema_version": IMAGE_SCHEMA_VERSION,
        "alt_text": alt_text,
        "is_decorative": is_dec,
        "align": align,
        "size_preset": size_preset,
    }
    if caption.strip():
        out["caption"] = caption
        out["caption_format"] = "limited_inline"
    return out, None


def verify_media_image_asset(cur, media_asset_id: int) -> bool:
    cur.execute(
        "SELECT media_type FROM media_assets WHERE media_asset_id = %s;",
        (media_asset_id,),
    )
    row = cur.fetchone()
    return row is not None and row[0] == "image"
