"""
Exam sheet PDF generation: split payload into sides/columns, render print-only HTML, generate PDF.
Uses same side/column split logic as frontend so output matches.
"""
import os
import io
from pathlib import Path

import markdown
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup


def _markdown_filter(text):
    if not text:
        return ""
    return Markup(markdown.markdown(text, extensions=["nl2br"]))


def split_payload_to_sides(payload):
    """Split topics into side A (front) and side B (back) by item count. Same logic as frontend."""
    topics = payload.get("topics") or []
    total = sum(len(t.get("terms") or []) + len(t.get("formulas") or []) for t in topics)
    side_a_target = (total + 1) // 2
    side_a_count = 0
    topics_side_a = []
    topics_side_b = []
    for topic in topics:
        topic_count = len(topic.get("terms") or []) + len(topic.get("formulas") or [])
        if side_a_count == 0 or side_a_count + topic_count <= side_a_target:
            topics_side_a.append(topic)
            side_a_count += topic_count
        else:
            topics_side_b.append(topic)
    return topics_side_a, topics_side_b


def _flatten_items(topics_list):
    """Yield (topic_handle, topic_name, 'term', term) or (..., 'formula', formula) in order."""
    for topic in topics_list:
        handle = topic.get("topic_handle") or ""
        name = topic.get("topic_name") or "Uncategorized"
        for t in topic.get("terms") or []:
            yield (handle, name, "term", t)
        for f in topic.get("formulas") or []:
            yield (handle, name, "formula", f)


def split_side_to_columns(topics_list):
    """Split one side's topics into left and right column topics (50/50 by item count)."""
    items = list(_flatten_items(topics_list))
    n = len(items)
    left_count = (n + 1) // 2
    left_items = items[:left_count]
    right_items = items[left_count:]

    def build_column_topics(item_list):
        buckets = {}
        order = []
        for topic_handle, topic_name, kind, obj in item_list:
            if topic_handle not in buckets:
                buckets[topic_handle] = {"topic_handle": topic_handle, "topic_name": topic_name, "terms": [], "formulas": []}
                order.append(topic_handle)
            b = buckets[topic_handle]
            if kind == "term":
                b["terms"].append(obj)
            else:
                b["formulas"].append(obj)
        return [buckets[h] for h in order]

    return build_column_topics(left_items), build_column_topics(right_items)


def render_print_html(payload, overflow_pages=None):
    """
    Render the exam sheet to print-only HTML.
    payload: dict with course_name, course_code, segment, topics
    overflow_pages: if set (e.g. 4), inject overflow banner on first page (optional).
    Returns HTML string.
    """
    topics_side_a, topics_side_b = split_payload_to_sides(payload)
    left_a, right_a = split_side_to_columns(topics_side_a)
    left_b, right_b = split_side_to_columns(topics_side_b)

    def has_content(topics_list):
        for t in topics_list:
            if (t.get("terms") or []) or (t.get("formulas") or []):
                return True
        return False

    no_content = not (has_content(left_a) or has_content(right_a) or has_content(left_b) or has_content(right_b))

    # Put the side that has content first so the first PDF page is never empty when there is content
    front = {"label": "Front side", "left_topics": left_a, "right_topics": right_a}
    back = {"label": "Back side", "left_topics": left_b, "right_topics": right_b}
    front_has_content = has_content(left_a) or has_content(right_a)
    back_has_content = has_content(left_b) or has_content(right_b)
    if back_has_content and not front_has_content:
        sides = [back, front]
    else:
        sides = [front, back]

    template_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(disabled_extensions=()),
    )
    env.filters["markdown"] = _markdown_filter
    template = env.get_template("exam_sheet_print.html")

    return template.render(
        course_name=payload.get("course_name") or "Course",
        course_code=payload.get("course_code"),
        segment=payload.get("segment") or "",
        sides=sides,
        overflow_pages=overflow_pages,
        no_content=no_content,
    )


def html_to_pdf(html_string):
    """
    Generate PDF from HTML using Playwright. Waits for MathJax to finish.
    Returns (pdf_bytes, page_count).
    """
    from playwright.sync_api import sync_playwright
    from pypdf import PdfReader

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html_string, wait_until="domcontentloaded")
            # Wait for MathJax to signal typesetting done (max 20s)
            try:
                page.wait_for_function(
                    "window.__MATHJAX_DONE__ === true",
                    timeout=20000,
                )
            except Exception:
                pass
            # Use print media so @page and page-break-after produce multiple PDF pages
            page.emulate_media(media="print")
            pdf_bytes = page.pdf(
                format="Letter",
                landscape=True,
                print_background=True,
                margin={"top": "10mm", "right": "10mm", "bottom": "10mm", "left": "10mm"},
            )
        finally:
            browser.close()

    reader = PdfReader(io.BytesIO(pdf_bytes))
    page_count = len(reader.pages)
    return pdf_bytes, page_count
