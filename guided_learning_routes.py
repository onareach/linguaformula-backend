"""
Guided learning API: checkpoints, lesson variants/pages/blocks, user progress, telemetry.
Registered from app.py via register_guided_learning_routes(app, ...).
"""
from flask import jsonify, request
from psycopg2.extras import Json

from guided_learning_blocks import validate_image_block_content, verify_media_image_asset

# Whitelist for tbl_user_activity_event.event_type (extend as product evolves)
def _normalize_block_content_dict(raw):
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        import json as _json

        try:
            o = _json.loads(raw)
            return o if isinstance(o, dict) else None
        except Exception:
            return None
    return None


def _media_blob_for_block(cur, block_type, media_asset_id):
    if block_type != "image" or media_asset_id is None:
        return None, None
    cur.execute(
        "SELECT blob_url, mime_type FROM media_assets WHERE media_asset_id = %s;",
        (media_asset_id,),
    )
    mr = cur.fetchone()
    if not mr:
        return None, None
    return mr[0], mr[1]


ALLOWED_ACTIVITY_EVENT_TYPES = frozenset(
    {
        "lesson_page_view",
        "lesson_started",
        "lesson_completed",
        "checkpoint_started",
        "checkpoint_completed",
        "question_launched",
        "term_opened",
        "formula_opened",
        "session_heartbeat",
    }
)


def register_guided_learning_routes(app, auth_db, get_current_user, require_admin):
    """Wire routes onto Flask app (call after _get_current_user / _require_admin exist)."""

    def _user_enrolled_catalog_for_segment(user_id, segment_id):
        """True if user is enrolled in any course whose catalog matches the segment's catalog."""
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1
            FROM tbl_segment s
            JOIN tbl_course c ON c.catalog_course_id = s.catalog_course_id
            JOIN tbl_user_course uc ON uc.course_id = c.course_id AND uc.user_id = %s
            WHERE s.segment_id = %s
            LIMIT 1;
            """,
            (user_id, segment_id),
        )
        ok = cur.fetchone() is not None
        cur.close()
        conn.close()
        return ok

    def _user_can_access_lesson_variant(user_id, lesson_variant_id):
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT s.segment_id
            FROM tbl_lesson_variant lv
            JOIN tbl_checkpoint cp ON cp.checkpoint_id = lv.checkpoint_id
            JOIN tbl_segment s ON s.segment_id = cp.segment_id
            WHERE lv.lesson_variant_id = %s;
            """,
            (lesson_variant_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return False
        return _user_enrolled_catalog_for_segment(user_id, row[0])

    # ---------- Admin: checkpoints ----------

    @app.route(
        "/api/admin/catalog-courses/<int:catalog_course_id>/segments/<int:segment_id>/checkpoints",
        methods=["GET"],
    )
    def admin_list_checkpoints(catalog_course_id, segment_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT catalog_course_id FROM tbl_segment WHERE segment_id = %s;",
            (segment_id,),
        )
        seg = cur.fetchone()
        if not seg or seg[0] != catalog_course_id:
            cur.close()
            conn.close()
            return jsonify({"error": "Segment not found for this catalog course"}), 404
        cur.execute(
            """
            SELECT checkpoint_id, segment_id, checkpoint_title, checkpoint_description,
                   checkpoint_order_index, is_required, created_at
            FROM tbl_checkpoint
            WHERE segment_id = %s
            ORDER BY checkpoint_order_index, checkpoint_id;
            """,
            (segment_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(
            {
                "checkpoints": [
                    {
                        "checkpoint_id": r[0],
                        "segment_id": r[1],
                        "checkpoint_title": r[2],
                        "checkpoint_description": r[3],
                        "checkpoint_order_index": r[4],
                        "is_required": r[5],
                        "created_at": r[6].isoformat() if r[6] else None,
                    }
                    for r in rows
                ]
            }
        )

    @app.route(
        "/api/admin/catalog-courses/<int:catalog_course_id>/segments/<int:segment_id>/checkpoints",
        methods=["POST"],
    )
    def admin_create_checkpoint(catalog_course_id, segment_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        title = (data.get("checkpoint_title") or data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "checkpoint_title is required"}), 400
        description = (data.get("checkpoint_description") or data.get("description") or "").strip() or None
        order_index = int(data.get("checkpoint_order_index", data.get("order_index", 0)) or 0)
        is_required = bool(data.get("is_required", False))
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT catalog_course_id FROM tbl_segment WHERE segment_id = %s;",
            (segment_id,),
        )
        seg = cur.fetchone()
        if not seg or seg[0] != catalog_course_id:
            cur.close()
            conn.close()
            return jsonify({"error": "Segment not found for this catalog course"}), 404
        cur.execute(
            """
            INSERT INTO tbl_checkpoint (segment_id, checkpoint_title, checkpoint_description, checkpoint_order_index, is_required)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING checkpoint_id, segment_id, checkpoint_title, checkpoint_description, checkpoint_order_index, is_required, created_at;
            """,
            (segment_id, title, description, order_index, is_required),
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return (
            jsonify(
                {
                    "checkpoint": {
                        "checkpoint_id": r[0],
                        "segment_id": r[1],
                        "checkpoint_title": r[2],
                        "checkpoint_description": r[3],
                        "checkpoint_order_index": r[4],
                        "is_required": r[5],
                        "created_at": r[6].isoformat() if r[6] else None,
                    }
                }
            ),
            201,
        )

    @app.route("/api/admin/checkpoints/<int:checkpoint_id>", methods=["PATCH"])
    def admin_patch_checkpoint(checkpoint_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        conn = auth_db()
        cur = conn.cursor()
        fields = []
        vals = []
        if "checkpoint_title" in data or "title" in data:
            t = (data.get("checkpoint_title") or data.get("title") or "").strip()
            if t:
                fields.append("checkpoint_title = %s")
                vals.append(t)
        if "checkpoint_description" in data or "description" in data:
            fields.append("checkpoint_description = %s")
            vals.append((data.get("checkpoint_description") or data.get("description") or "").strip() or None)
        if "checkpoint_order_index" in data or "order_index" in data:
            fields.append("checkpoint_order_index = %s")
            vals.append(int(data.get("checkpoint_order_index", data.get("order_index", 0)) or 0))
        if "is_required" in data:
            fields.append("is_required = %s")
            vals.append(bool(data["is_required"]))
        if not fields:
            cur.close()
            conn.close()
            return jsonify({"error": "No updatable fields"}), 400
        vals.append(checkpoint_id)
        cur.execute(
            f"UPDATE tbl_checkpoint SET {', '.join(fields)} WHERE checkpoint_id = %s RETURNING checkpoint_id, segment_id, checkpoint_title, checkpoint_description, checkpoint_order_index, is_required, created_at;",
            vals,
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Checkpoint not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "checkpoint": {
                    "checkpoint_id": r[0],
                    "segment_id": r[1],
                    "checkpoint_title": r[2],
                    "checkpoint_description": r[3],
                    "checkpoint_order_index": r[4],
                    "is_required": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                }
            }
        )

    @app.route("/api/admin/checkpoints/<int:checkpoint_id>", methods=["DELETE"])
    def admin_delete_checkpoint(checkpoint_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM tbl_checkpoint WHERE checkpoint_id = %s RETURNING checkpoint_id;", (checkpoint_id,))
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Checkpoint not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    # ---------- Admin: lesson variants ----------

    @app.route("/api/admin/checkpoints/<int:checkpoint_id>/lesson-variants", methods=["GET"])
    def admin_list_lesson_variants(checkpoint_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT lesson_variant_id, checkpoint_id, variant_label, variant_type, variant_order_index, is_default, created_at
            FROM tbl_lesson_variant
            WHERE checkpoint_id = %s
            ORDER BY variant_order_index, lesson_variant_id;
            """,
            (checkpoint_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(
            {
                "lesson_variants": [
                    {
                        "lesson_variant_id": r[0],
                        "checkpoint_id": r[1],
                        "variant_label": r[2],
                        "variant_type": r[3],
                        "variant_order_index": r[4],
                        "is_default": r[5],
                        "created_at": r[6].isoformat() if r[6] else None,
                    }
                    for r in rows
                ]
            }
        )

    @app.route("/api/admin/checkpoints/<int:checkpoint_id>/lesson-variants", methods=["POST"])
    def admin_create_lesson_variant(checkpoint_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        label = (data.get("variant_label") or "").strip()
        if not label:
            return jsonify({"error": "variant_label is required"}), 400
        vtype = (data.get("variant_type") or "other").strip().lower()
        if vtype not in ("direct", "quick", "full", "other"):
            return jsonify({"error": "invalid variant_type"}), 400
        order_index = int(data.get("variant_order_index", 0) or 0)
        is_default = bool(data.get("is_default", False))
        conn = auth_db()
        cur = conn.cursor()
        if is_default:
            cur.execute(
                "UPDATE tbl_lesson_variant SET is_default = false WHERE checkpoint_id = %s;",
                (checkpoint_id,),
            )
        cur.execute(
            """
            INSERT INTO tbl_lesson_variant (checkpoint_id, variant_label, variant_type, variant_order_index, is_default)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING lesson_variant_id, checkpoint_id, variant_label, variant_type, variant_order_index, is_default, created_at;
            """,
            (checkpoint_id, label, vtype, order_index, is_default),
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return (
            jsonify(
                {
                    "lesson_variant": {
                        "lesson_variant_id": r[0],
                        "checkpoint_id": r[1],
                        "variant_label": r[2],
                        "variant_type": r[3],
                        "variant_order_index": r[4],
                        "is_default": r[5],
                        "created_at": r[6].isoformat() if r[6] else None,
                    }
                }
            ),
            201,
        )

    @app.route("/api/admin/lesson-variants/<int:lesson_variant_id>", methods=["PATCH"])
    def admin_patch_lesson_variant(lesson_variant_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        conn = auth_db()
        cur = conn.cursor()
        cur.execute("SELECT checkpoint_id FROM tbl_lesson_variant WHERE lesson_variant_id = %s;", (lesson_variant_id,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Lesson variant not found"}), 404
        checkpoint_id = row[0]
        if bool(data.get("is_default")):
            cur.execute(
                "UPDATE tbl_lesson_variant SET is_default = false WHERE checkpoint_id = %s;",
                (checkpoint_id,),
            )
        fields = []
        vals = []
        if "variant_label" in data:
            fields.append("variant_label = %s")
            vals.append((data.get("variant_label") or "").strip())
        if "variant_type" in data:
            v = (data.get("variant_type") or "").strip().lower()
            if v not in ("direct", "quick", "full", "other"):
                cur.close()
                conn.close()
                return jsonify({"error": "invalid variant_type"}), 400
            fields.append("variant_type = %s")
            vals.append(v)
        if "variant_order_index" in data:
            fields.append("variant_order_index = %s")
            vals.append(int(data["variant_order_index"] or 0))
        if "is_default" in data:
            fields.append("is_default = %s")
            vals.append(bool(data["is_default"]))
        if not fields:
            cur.close()
            conn.close()
            return jsonify({"error": "No updatable fields"}), 400
        vals.append(lesson_variant_id)
        cur.execute(
            f"UPDATE tbl_lesson_variant SET {', '.join(fields)} WHERE lesson_variant_id = %s RETURNING lesson_variant_id, checkpoint_id, variant_label, variant_type, variant_order_index, is_default, created_at;",
            vals,
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "lesson_variant": {
                    "lesson_variant_id": r[0],
                    "checkpoint_id": r[1],
                    "variant_label": r[2],
                    "variant_type": r[3],
                    "variant_order_index": r[4],
                    "is_default": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                }
            }
        )

    @app.route("/api/admin/lesson-variants/<int:lesson_variant_id>", methods=["DELETE"])
    def admin_delete_lesson_variant(lesson_variant_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM tbl_lesson_variant WHERE lesson_variant_id = %s RETURNING lesson_variant_id;",
            (lesson_variant_id,),
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Lesson variant not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    # ---------- Admin: pages & blocks ----------

    @app.route("/api/admin/lesson-variants/<int:lesson_variant_id>/pages", methods=["GET"])
    def admin_list_lesson_pages(lesson_variant_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT lesson_page_id, lesson_variant_id, page_title, page_order_index, created_at
            FROM tbl_lesson_page
            WHERE lesson_variant_id = %s
            ORDER BY page_order_index, lesson_page_id;
            """,
            (lesson_variant_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify(
            {
                "pages": [
                    {
                        "lesson_page_id": r[0],
                        "lesson_variant_id": r[1],
                        "page_title": r[2],
                        "page_order_index": r[3],
                        "created_at": r[4].isoformat() if r[4] else None,
                    }
                    for r in rows
                ]
            }
        )

    @app.route("/api/admin/lesson-variants/<int:lesson_variant_id>/pages", methods=["POST"])
    def admin_create_lesson_page(lesson_variant_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        title = (data.get("page_title") or "").strip() or None
        order_index = int(data.get("page_order_index", 0) or 0)
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tbl_lesson_page (lesson_variant_id, page_title, page_order_index)
            VALUES (%s, %s, %s)
            RETURNING lesson_page_id, lesson_variant_id, page_title, page_order_index, created_at;
            """,
            (lesson_variant_id, title, order_index),
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return (
            jsonify(
                {
                    "page": {
                        "lesson_page_id": r[0],
                        "lesson_variant_id": r[1],
                        "page_title": r[2],
                        "page_order_index": r[3],
                        "created_at": r[4].isoformat() if r[4] else None,
                    }
                }
            ),
            201,
        )

    @app.route("/api/admin/lesson-pages/<int:lesson_page_id>", methods=["PATCH"])
    def admin_patch_lesson_page(lesson_page_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        conn = auth_db()
        cur = conn.cursor()
        fields = []
        vals = []
        if "page_title" in data:
            fields.append("page_title = %s")
            vals.append((data.get("page_title") or "").strip() or None)
        if "page_order_index" in data:
            fields.append("page_order_index = %s")
            vals.append(int(data["page_order_index"] or 0))
        if not fields:
            cur.close()
            conn.close()
            return jsonify({"error": "No updatable fields"}), 400
        vals.append(lesson_page_id)
        cur.execute(
            f"UPDATE tbl_lesson_page SET {', '.join(fields)} WHERE lesson_page_id = %s RETURNING lesson_page_id, lesson_variant_id, page_title, page_order_index, created_at;",
            vals,
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Page not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify(
            {
                "page": {
                    "lesson_page_id": r[0],
                    "lesson_variant_id": r[1],
                    "page_title": r[2],
                    "page_order_index": r[3],
                    "created_at": r[4].isoformat() if r[4] else None,
                }
            }
        )

    @app.route("/api/admin/lesson-pages/<int:lesson_page_id>", methods=["DELETE"])
    def admin_delete_lesson_page(lesson_page_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM tbl_lesson_page WHERE lesson_page_id = %s RETURNING lesson_page_id;", (lesson_page_id,))
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Page not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    @app.route("/api/admin/lesson-pages/<int:lesson_page_id>/blocks", methods=["GET"])
    def admin_list_blocks(lesson_page_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT b.lesson_block_id, b.lesson_page_id, b.block_type, b.block_content, b.block_order_index,
                   b.linked_term_id, b.linked_formula_id, b.linked_question_id, b.launch_mode, b.media_asset_id,
                   b.created_at, m.blob_url, m.mime_type
            FROM tbl_lesson_block b
            LEFT JOIN media_assets m
              ON m.media_asset_id = b.media_asset_id AND b.block_type = 'image'
            WHERE b.lesson_page_id = %s
            ORDER BY b.block_order_index, b.lesson_block_id;
            """,
            (lesson_page_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        def _content(c):
            if c is None:
                return None
            if isinstance(c, dict):
                return c
            return c

        return jsonify(
            {
                "blocks": [
                    {
                        "lesson_block_id": r[0],
                        "lesson_page_id": r[1],
                        "block_type": r[2],
                        "block_content": _content(r[3]),
                        "block_order_index": r[4],
                        "linked_term_id": r[5],
                        "linked_formula_id": r[6],
                        "linked_question_id": r[7],
                        "launch_mode": r[8],
                        "media_asset_id": r[9],
                        "created_at": r[10].isoformat() if r[10] else None,
                        "blob_url": r[11],
                        "mime_type": r[12],
                    }
                    for r in rows
                ]
            }
        )

    @app.route("/api/admin/lesson-pages/<int:lesson_page_id>/blocks", methods=["POST"])
    def admin_create_block(lesson_page_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        block_type = (data.get("block_type") or "").strip()
        if not block_type:
            return jsonify({"error": "block_type is required"}), 400
        block_content = data.get("block_content")
        order_index = int(data.get("block_order_index", 0) or 0)
        lt = data.get("linked_term_id")
        lf = data.get("linked_formula_id")
        lq = data.get("linked_question_id")
        launch_mode_raw = data.get("launch_mode")
        media_asset_id = data.get("media_asset_id")

        conn = auth_db()
        cur = conn.cursor()

        if block_type == "image":
            if media_asset_id is None:
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_id_required"}), 400
            try:
                media_asset_id = int(media_asset_id)
            except (TypeError, ValueError):
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_id_invalid"}), 400
            out_content, v_err = validate_image_block_content(block_content)
            if v_err:
                cur.close()
                conn.close()
                return jsonify({"error": v_err}), 400
            if not verify_media_image_asset(cur, media_asset_id):
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_invalid"}), 400
            lt = lf = lq = None
            launch_mode = None
            block_content = out_content
        else:
            if media_asset_id is not None:
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_id_not_allowed"}), 400
            media_asset_id = None
            lm = (launch_mode_raw if launch_mode_raw is not None else "same_tab")
            if not isinstance(lm, str):
                cur.close()
                conn.close()
                return jsonify({"error": "invalid launch_mode"}), 400
            launch_mode = lm.strip().lower()
            if launch_mode not in ("same_tab", "new_tab", "modal"):
                cur.close()
                conn.close()
                return jsonify({"error": "invalid launch_mode"}), 400

        cur.execute(
            """
            INSERT INTO tbl_lesson_block (
              lesson_page_id, block_type, block_content, block_order_index,
              linked_term_id, linked_formula_id, linked_question_id, launch_mode, media_asset_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING lesson_block_id, lesson_page_id, block_type, block_content, block_order_index,
                      linked_term_id, linked_formula_id, linked_question_id, launch_mode, media_asset_id, created_at;
            """,
            (
                lesson_page_id,
                block_type,
                Json(block_content) if block_content is not None else None,
                order_index,
                lt,
                lf,
                lq,
                launch_mode,
                media_asset_id,
            ),
        )
        r = cur.fetchone()
        conn.commit()
        bc = r[3]
        if bc is not None and not isinstance(bc, dict):
            try:
                import json as _json

                bc = _json.loads(bc) if isinstance(bc, str) else bc
            except Exception:
                pass
        blob_url, mime_type = _media_blob_for_block(cur, r[2], r[9])
        cur.close()
        conn.close()
        return (
            jsonify(
                {
                    "block": {
                        "lesson_block_id": r[0],
                        "lesson_page_id": r[1],
                        "block_type": r[2],
                        "block_content": bc,
                        "block_order_index": r[4],
                        "linked_term_id": r[5],
                        "linked_formula_id": r[6],
                        "linked_question_id": r[7],
                        "launch_mode": r[8],
                        "media_asset_id": r[9],
                        "created_at": r[10].isoformat() if r[10] else None,
                        "blob_url": blob_url,
                        "mime_type": mime_type,
                    }
                }
            ),
            201,
        )

    @app.route("/api/admin/lesson-blocks/<int:lesson_block_id>", methods=["PATCH"])
    def admin_patch_block(lesson_block_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        if not data:
            return jsonify({"error": "No updatable fields"}), 400
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT lesson_page_id, block_type, block_content, block_order_index,
                   linked_term_id, linked_formula_id, linked_question_id, launch_mode, media_asset_id
            FROM tbl_lesson_block WHERE lesson_block_id = %s;
            """,
            (lesson_block_id,),
        )
        cur_row = cur.fetchone()
        if not cur_row:
            cur.close()
            conn.close()
            return jsonify({"error": "Block not found"}), 404

        cur_bt = cur_row[1]
        cur_bc = _normalize_block_content_dict(cur_row[2])
        cur_bo = cur_row[3]
        cur_lt, cur_lf, cur_lq = cur_row[4], cur_row[5], cur_row[6]
        cur_lm, cur_ma = cur_row[7], cur_row[8]

        merged_type = (data.get("block_type") or "").strip() if "block_type" in data else cur_bt
        if not merged_type:
            merged_type = cur_bt
        merged_bc = data["block_content"] if "block_content" in data else cur_bc
        merged_bo = int(data["block_order_index"] or 0) if "block_order_index" in data else cur_bo
        merged_lt = data["linked_term_id"] if "linked_term_id" in data else cur_lt
        merged_lf = data["linked_formula_id"] if "linked_formula_id" in data else cur_lf
        merged_lq = data["linked_question_id"] if "linked_question_id" in data else cur_lq
        if "launch_mode" in data:
            lm = data.get("launch_mode")
            if lm is None or (isinstance(lm, str) and lm.strip() == ""):
                merged_lm = "same_tab"
            elif not isinstance(lm, str) or lm.strip().lower() not in ("same_tab", "new_tab", "modal"):
                cur.close()
                conn.close()
                return jsonify({"error": "invalid launch_mode"}), 400
            else:
                merged_lm = lm.strip().lower()
        else:
            merged_lm = cur_lm if cur_lm is not None else "same_tab"
        merged_ma = data["media_asset_id"] if "media_asset_id" in data else cur_ma

        recognized_keys = {
            "block_type",
            "block_content",
            "block_order_index",
            "linked_term_id",
            "linked_formula_id",
            "linked_question_id",
            "launch_mode",
            "media_asset_id",
        }
        if not any(k in data for k in recognized_keys):
            cur.close()
            conn.close()
            return jsonify({"error": "No updatable fields"}), 400

        if merged_type == "image":
            if merged_ma is None:
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_id_required"}), 400
            try:
                merged_ma = int(merged_ma)
            except (TypeError, ValueError):
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_id_invalid"}), 400
            out_content, v_err = validate_image_block_content(merged_bc)
            if v_err:
                cur.close()
                conn.close()
                return jsonify({"error": v_err}), 400
            if not verify_media_image_asset(cur, merged_ma):
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_invalid"}), 400
            merged_lt = merged_lf = merged_lq = None
            merged_lm = None
            merged_bc = out_content
        else:
            if "media_asset_id" in data and data["media_asset_id"] is not None:
                cur.close()
                conn.close()
                return jsonify({"error": "media_asset_id_not_allowed"}), 400
            merged_ma = None
            if merged_lm is None or (isinstance(merged_lm, str) and merged_lm.strip() == ""):
                merged_lm = "same_tab"
            if isinstance(merged_lm, str):
                merged_lm = merged_lm.strip().lower()
            if merged_lm not in ("same_tab", "new_tab", "modal"):
                cur.close()
                conn.close()
                return jsonify({"error": "invalid launch_mode"}), 400

        cur.execute(
            """
            UPDATE tbl_lesson_block SET
              block_type = %s,
              block_content = %s,
              block_order_index = %s,
              linked_term_id = %s,
              linked_formula_id = %s,
              linked_question_id = %s,
              launch_mode = %s,
              media_asset_id = %s
            WHERE lesson_block_id = %s
            RETURNING lesson_block_id, lesson_page_id, block_type, block_content, block_order_index,
                      linked_term_id, linked_formula_id, linked_question_id, launch_mode, media_asset_id, created_at;
            """,
            (
                merged_type,
                Json(merged_bc) if merged_bc is not None else None,
                merged_bo,
                merged_lt,
                merged_lf,
                merged_lq,
                merged_lm,
                merged_ma,
                lesson_block_id,
            ),
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Block not found"}), 404
        conn.commit()
        bc = r[3]
        if bc is not None and not isinstance(bc, dict):
            try:
                import json as _json

                bc = _json.loads(bc) if isinstance(bc, str) else bc
            except Exception:
                pass
        blob_url, mime_type = _media_blob_for_block(cur, r[2], r[9])
        cur.close()
        conn.close()
        return jsonify(
            {
                "block": {
                    "lesson_block_id": r[0],
                    "lesson_page_id": r[1],
                    "block_type": r[2],
                    "block_content": bc,
                    "block_order_index": r[4],
                    "linked_term_id": r[5],
                    "linked_formula_id": r[6],
                    "linked_question_id": r[7],
                    "launch_mode": r[8],
                    "media_asset_id": r[9],
                    "created_at": r[10].isoformat() if r[10] else None,
                    "blob_url": blob_url,
                    "mime_type": mime_type,
                }
            }
        )

    @app.route("/api/admin/lesson-blocks/<int:lesson_block_id>", methods=["DELETE"])
    def admin_delete_block(lesson_block_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM tbl_lesson_block WHERE lesson_block_id = %s RETURNING lesson_block_id;",
            (lesson_block_id,),
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Block not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    # ---------- Admin: checkpoint questions ----------

    @app.route("/api/admin/checkpoints/<int:checkpoint_id>/questions", methods=["GET"])
    def admin_list_checkpoint_questions(checkpoint_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT cq.question_id, cq.display_order
            FROM tbl_checkpoint_question cq
            WHERE cq.checkpoint_id = %s
            ORDER BY cq.display_order, cq.question_id;
            """,
            (checkpoint_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"questions": [{"question_id": r[0], "display_order": r[1]} for r in rows]})

    @app.route("/api/admin/checkpoints/<int:checkpoint_id>/questions", methods=["POST"])
    def admin_add_checkpoint_question(checkpoint_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        data = request.get_json() or {}
        qid = data.get("question_id")
        if qid is None:
            return jsonify({"error": "question_id is required"}), 400
        qid = int(qid)
        display_order = int(data.get("display_order", 0) or 0)
        conn = auth_db()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO tbl_checkpoint_question (checkpoint_id, question_id, display_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (checkpoint_id, question_id) DO UPDATE SET display_order = EXCLUDED.display_order;
                """,
                (checkpoint_id, qid, display_order),
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": str(e)}), 400
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    @app.route(
        "/api/admin/checkpoints/<int:checkpoint_id>/questions/<int:question_id>",
        methods=["PATCH", "DELETE"],
    )
    def admin_checkpoint_question_item(checkpoint_id, question_id):
        claims, err = require_admin()
        if err:
            return err[0], err[1]
        if request.method == "PATCH":
            data = request.get_json() or {}
            if "display_order" not in data:
                return jsonify({"error": "display_order is required"}), 400
            display_order = int(data.get("display_order", 0) or 0)
            conn = auth_db()
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE tbl_checkpoint_question
                SET display_order = %s
                WHERE checkpoint_id = %s AND question_id = %s
                RETURNING checkpoint_id, question_id, display_order;
                """,
                (display_order, checkpoint_id, question_id),
            )
            row = cur.fetchone()
            if not row:
                conn.rollback()
                cur.close()
                conn.close()
                return jsonify({"error": "Link not found"}), 404
            conn.commit()
            cur.close()
            conn.close()
            return jsonify(
                {
                    "question": {
                        "question_id": row[1],
                        "display_order": row[2],
                    }
                }
            )
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM tbl_checkpoint_question WHERE checkpoint_id = %s AND question_id = %s;",
            (checkpoint_id, question_id),
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    # ---------- User: checkpoints & lesson payload ----------

    @app.route("/api/courses/<int:course_id>/segments/<int:segment_id>/checkpoints", methods=["GET"])
    def user_list_checkpoints(course_id, segment_id):
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.catalog_course_id FROM tbl_user_course uc
            JOIN tbl_course c ON c.course_id = uc.course_id
            WHERE uc.user_id = %s AND uc.course_id = %s;
            """,
            (user_id, course_id),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Not enrolled in this course"}), 403
        catalog_course_id = row[0]
        cur.execute(
            "SELECT catalog_course_id FROM tbl_segment WHERE segment_id = %s;",
            (segment_id,),
        )
        seg = cur.fetchone()
        if not seg or seg[0] != catalog_course_id:
            cur.close()
            conn.close()
            return jsonify({"error": "Segment does not belong to this course's catalog"}), 404
        cur.execute(
            """
            SELECT checkpoint_id, segment_id, checkpoint_title, checkpoint_description,
                   checkpoint_order_index, is_required, created_at
            FROM tbl_checkpoint
            WHERE segment_id = %s
            ORDER BY checkpoint_order_index, checkpoint_id;
            """,
            (segment_id,),
        )
        cps = cur.fetchall()
        checkpoints_out = []
        for cp in cps:
            cid = cp[0]
            cur.execute(
                """
                SELECT lesson_variant_id, variant_label, variant_type, variant_order_index, is_default
                FROM tbl_lesson_variant
                WHERE checkpoint_id = %s
                ORDER BY variant_order_index, lesson_variant_id;
                """,
                (cid,),
            )
            variants = [
                {
                    "lesson_variant_id": v[0],
                    "variant_label": v[1],
                    "variant_type": v[2],
                    "variant_order_index": v[3],
                    "is_default": v[4],
                }
                for v in cur.fetchall()
            ]
            checkpoints_out.append(
                {
                    "checkpoint_id": cp[0],
                    "segment_id": cp[1],
                    "checkpoint_title": cp[2],
                    "checkpoint_description": cp[3],
                    "checkpoint_order_index": cp[4],
                    "is_required": cp[5],
                    "created_at": cp[6].isoformat() if cp[6] else None,
                    "lesson_variants": variants,
                }
            )
        cur.close()
        conn.close()
        return jsonify({"checkpoints": checkpoints_out})

    @app.route("/api/learn/lesson-variants/<int:lesson_variant_id>", methods=["GET"])
    def user_get_lesson_variant(lesson_variant_id):
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        if not _user_can_access_lesson_variant(user_id, lesson_variant_id):
            return jsonify({"error": "Forbidden or not found"}), 403
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT lesson_variant_id, checkpoint_id, variant_label, variant_type, variant_order_index, is_default, created_at
            FROM tbl_lesson_variant WHERE lesson_variant_id = %s;
            """,
            (lesson_variant_id,),
        )
        vrow = cur.fetchone()
        if not vrow:
            cur.close()
            conn.close()
            return jsonify({"error": "Not found"}), 404
        cur.execute(
            """
            SELECT lesson_page_id, page_title, page_order_index, created_at
            FROM tbl_lesson_page
            WHERE lesson_variant_id = %s
            ORDER BY page_order_index, lesson_page_id;
            """,
            (lesson_variant_id,),
        )
        pages = []
        for prow in cur.fetchall():
            pid = prow[0]
            cur.execute(
                """
                SELECT lb.lesson_block_id, lb.block_type, lb.block_content, lb.block_order_index,
                       lb.linked_term_id, lb.linked_formula_id, lb.linked_question_id, lb.launch_mode,
                       lb.media_asset_id, m.blob_url, m.mime_type
                FROM tbl_lesson_block lb
                LEFT JOIN media_assets m
                  ON m.media_asset_id = lb.media_asset_id AND lb.block_type = 'image'
                WHERE lb.lesson_page_id = %s
                ORDER BY lb.block_order_index, lb.lesson_block_id;
                """,
                (pid,),
            )
            blocks = []
            for br in cur.fetchall():
                bc = br[2]
                if bc is not None and not isinstance(bc, dict):
                    try:
                        import json as _json

                        bc = _json.loads(bc) if isinstance(bc, str) else bc
                    except Exception:
                        pass
                bt = br[1]
                blocks.append(
                    {
                        "lesson_block_id": br[0],
                        "block_type": bt,
                        "block_content": bc,
                        "block_order_index": br[3],
                        "linked_term_id": br[4],
                        "linked_formula_id": br[5],
                        "linked_question_id": br[6],
                        "launch_mode": br[7],
                        "media_asset_id": br[8],
                        "blob_url": br[9] if bt == "image" else None,
                        "mime_type": br[10] if bt == "image" else None,
                    }
                )
            pages.append(
                {
                    "lesson_page_id": pid,
                    "page_title": prow[1],
                    "page_order_index": prow[2],
                    "created_at": prow[3].isoformat() if prow[3] else None,
                    "blocks": blocks,
                }
            )
        cur.execute(
            """
            SELECT s.segment_name, c.course_id
            FROM tbl_lesson_variant lv
            JOIN tbl_checkpoint cp ON cp.checkpoint_id = lv.checkpoint_id
            JOIN tbl_segment s ON s.segment_id = cp.segment_id
            JOIN tbl_course c ON c.catalog_course_id = s.catalog_course_id
            JOIN tbl_user_course uc ON uc.course_id = c.course_id AND uc.user_id = %s
            WHERE lv.lesson_variant_id = %s
            ORDER BY c.course_id
            LIMIT 1;
            """,
            (user_id, lesson_variant_id),
        )
        ctx_row = cur.fetchone()
        self_testing_context = None
        if ctx_row is not None:
            self_testing_context = {
                "segment_name": ctx_row[0],
                "course_id": ctx_row[1],
            }
        cur.close()
        conn.close()
        lesson_variant_out = {
            "lesson_variant_id": vrow[0],
            "checkpoint_id": vrow[1],
            "variant_label": vrow[2],
            "variant_type": vrow[3],
            "variant_order_index": vrow[4],
            "is_default": vrow[5],
            "created_at": vrow[6].isoformat() if vrow[6] else None,
            "pages": pages,
        }
        if self_testing_context is not None:
            lesson_variant_out["self_testing_context"] = self_testing_context
        return jsonify({"lesson_variant": lesson_variant_out})

    def _learn_fetch_question_payload(cur, qid):
        """JSON for learner routes: like admin question shape, plus answer_id and formula_id for self-testing."""
        cur.execute(
            """
            SELECT question_id, question_handle, question_type, stem, explanation, display_order,
                   parent_question_id
            FROM tbl_question WHERE question_id = %s;
            """,
            (qid,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        q_id, qhandle, qtype, stem, explanation, display_order, parent_id = row
        cur.execute(
            """
            SELECT a.answer_id, a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
            FROM tbl_question_answer qa
            INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
            WHERE qa.question_id = %s
            ORDER BY qa.display_order, qa.question_answer_id;
            """,
            (q_id,),
        )
        answers = [
            {
                "answer_id": r[0],
                "answer_text": r[1] or "",
                "answer_numeric": float(r[2]) if r[2] is not None else None,
                "is_correct": r[3],
                "display_order": r[4],
            }
            for r in cur.fetchall()
        ]
        cur.execute("SELECT formula_id FROM tbl_formula_question WHERE question_id = %s;", (q_id,))
        formula_ids = [r[0] for r in cur.fetchall()]
        cur.execute("SELECT term_id FROM tbl_term_question WHERE question_id = %s;", (q_id,))
        term_ids = [r[0] for r in cur.fetchall()]
        item = {
            "question_id": q_id,
            "question_handle": qhandle,
            "question_type": qtype,
            "stem": stem or "",
            "explanation": explanation or "",
            "display_order": display_order,
            "answers": answers,
            "formula_ids": formula_ids,
            "term_ids": term_ids,
        }
        if formula_ids:
            item["formula_id"] = formula_ids[0]
        if parent_id is not None:
            item["parent_question_id"] = parent_id
        if qtype == "multipart" and parent_id is None:
            cur.execute(
                """
                SELECT question_id, question_handle, part_label, stem, display_order
                FROM tbl_question
                WHERE parent_question_id = %s
                ORDER BY display_order, question_id;
                """,
                (q_id,),
            )
            parts = []
            for pr in cur.fetchall():
                pid, phandle, plabel, pstem, pord = pr
                cur.execute(
                    """
                    SELECT a.answer_id, a.answer_text, a.answer_numeric, qa.is_correct, qa.display_order
                    FROM tbl_question_answer qa
                    INNER JOIN tbl_answer a ON a.answer_id = qa.answer_id
                    WHERE qa.question_id = %s
                    ORDER BY qa.display_order;
                    """,
                    (pid,),
                )
                part_answers = [
                    {
                        "answer_id": r[0],
                        "answer_text": r[1] or "",
                        "answer_numeric": float(r[2]) if r[2] is not None else None,
                        "is_correct": r[3],
                        "display_order": r[4],
                    }
                    for r in cur.fetchall()
                ]
                parts.append(
                    {
                        "question_id": pid,
                        "question_handle": phandle,
                        "part_label": plabel or "",
                        "stem": pstem or "",
                        "display_order": pord,
                        "answers": part_answers,
                    }
                )
            item["parts"] = parts
        return item

    @app.route("/api/learn/questions/<int:question_id>", methods=["GET"])
    def user_get_question_for_lesson(question_id):
        """Return question JSON for a learner when it is linked from a lesson block they may open.

        Requires `lesson_variant_id` query param; user must be enrolled for that variant's segment
        and the variant must contain a block with this `linked_question_id`.
        """
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        lvid_raw = request.args.get("lesson_variant_id")
        if lvid_raw is None or str(lvid_raw).strip() == "":
            return jsonify({"error": "lesson_variant_id query parameter is required"}), 400
        try:
            lesson_variant_id = int(lvid_raw)
        except (TypeError, ValueError):
            return jsonify({"error": "invalid lesson_variant_id"}), 400
        if not _user_can_access_lesson_variant(user_id, lesson_variant_id):
            return jsonify({"error": "Forbidden or not found"}), 403

        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT 1 FROM tbl_lesson_block lb
            INNER JOIN tbl_lesson_page lp ON lp.lesson_page_id = lb.lesson_page_id
            WHERE lp.lesson_variant_id = %s AND lb.linked_question_id = %s
            LIMIT 1;
            """,
            (lesson_variant_id, question_id),
        )
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({"error": "Question is not linked from this lesson"}), 403

        item = _learn_fetch_question_payload(cur, question_id)
        cur.close()
        conn.close()
        if item is None:
            return jsonify({"error": "Question not found"}), 404
        return jsonify(item)

    # ---------- User: progress ----------

    @app.route("/api/learn/checkpoint-paths", methods=["POST"])
    def user_start_checkpoint_path():
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        data = request.get_json() or {}
        checkpoint_id = data.get("checkpoint_id")
        if checkpoint_id is None:
            return jsonify({"error": "checkpoint_id is required"}), 400
        checkpoint_id = int(checkpoint_id)
        lesson_variant_id = data.get("lesson_variant_id")
        if lesson_variant_id is not None:
            lesson_variant_id = int(lesson_variant_id)
        path_type = (data.get("path_type") or "other").strip().lower()
        if path_type not in ("direct", "quick", "full", "other"):
            return jsonify({"error": "invalid path_type"}), 400
        conn = auth_db()
        cur = conn.cursor()
        cur.execute("SELECT segment_id FROM tbl_checkpoint WHERE checkpoint_id = %s;", (checkpoint_id,))
        cp = cur.fetchone()
        if not cp:
            cur.close()
            conn.close()
            return jsonify({"error": "Checkpoint not found"}), 404
        if not _user_enrolled_catalog_for_segment(user_id, cp[0]):
            cur.close()
            conn.close()
            return jsonify({"error": "Forbidden"}), 403
        if lesson_variant_id is not None:
            cur.execute(
                "SELECT checkpoint_id FROM tbl_lesson_variant WHERE lesson_variant_id = %s;",
                (lesson_variant_id,),
            )
            vr = cur.fetchone()
            if not vr or vr[0] != checkpoint_id:
                cur.close()
                conn.close()
                return jsonify({"error": "Lesson variant does not match checkpoint"}), 400
        cur.execute(
            """
            INSERT INTO tbl_user_checkpoint_path (user_id, checkpoint_id, lesson_variant_id, path_type, status)
            VALUES (%s, %s, %s, %s, 'in_progress')
            RETURNING user_checkpoint_path_id, started_timestamp;
            """,
            (user_id, checkpoint_id, lesson_variant_id, path_type),
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return (
            jsonify(
                {
                    "user_checkpoint_path_id": r[0],
                    "started_timestamp": r[1].isoformat() if r[1] else None,
                }
            ),
            201,
        )

    @app.route("/api/learn/checkpoint-paths/<int:path_id>/complete", methods=["POST"])
    def user_complete_checkpoint_path(path_id):
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE tbl_user_checkpoint_path
            SET status = 'completed', completed_timestamp = CURRENT_TIMESTAMP
            WHERE user_checkpoint_path_id = %s AND user_id = %s
            RETURNING user_checkpoint_path_id;
            """,
            (path_id, user_id),
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    @app.route("/api/learn/checkpoint-paths/<int:path_id>/abandon", methods=["POST"])
    def user_abandon_checkpoint_path(path_id):
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE tbl_user_checkpoint_path
            SET status = 'abandoned', abandoned_timestamp = CURRENT_TIMESTAMP
            WHERE user_checkpoint_path_id = %s AND user_id = %s
            RETURNING user_checkpoint_path_id;
            """,
            (path_id, user_id),
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    @app.route("/api/learn/lesson-progress", methods=["POST"])
    def user_start_or_update_lesson_progress():
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        data = request.get_json() or {}
        lesson_variant_id = data.get("lesson_variant_id")
        if lesson_variant_id is None:
            return jsonify({"error": "lesson_variant_id is required"}), 400
        lesson_variant_id = int(lesson_variant_id)
        if not _user_can_access_lesson_variant(user_id, lesson_variant_id):
            return jsonify({"error": "Forbidden"}), 403
        current_page_id = data.get("current_page_id")
        if current_page_id is not None:
            current_page_id = int(current_page_id)
        status = (data.get("status") or "in_progress").strip().lower()
        if status not in ("in_progress", "completed", "abandoned"):
            return jsonify({"error": "invalid status"}), 400
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_lesson_progress_id FROM tbl_user_lesson_progress
            WHERE user_id = %s AND lesson_variant_id = %s;
            """,
            (user_id, lesson_variant_id),
        )
        existing = cur.fetchone()
        completed_ts = "CURRENT_TIMESTAMP" if status == "completed" else "completed_timestamp"
        if existing:
            if current_page_id is not None:
                cur.execute(
                    f"""
                    UPDATE tbl_user_lesson_progress
                    SET status = %s,
                        last_activity_timestamp = CURRENT_TIMESTAMP,
                        current_page_id = %s,
                        completed_timestamp = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_timestamp END
                    WHERE user_id = %s AND lesson_variant_id = %s
                    RETURNING user_lesson_progress_id;
                    """,
                    (status, current_page_id, status, user_id, lesson_variant_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE tbl_user_lesson_progress
                    SET status = %s,
                        last_activity_timestamp = CURRENT_TIMESTAMP,
                        completed_timestamp = CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_timestamp END
                    WHERE user_id = %s AND lesson_variant_id = %s
                    RETURNING user_lesson_progress_id;
                    """,
                    (status, status, user_id, lesson_variant_id),
                )
        else:
            cur.execute(
                """
                INSERT INTO tbl_user_lesson_progress (
                  user_id, lesson_variant_id, current_page_id, status,
                  completed_timestamp
                )
                VALUES (%s, %s, %s, %s,
                  CASE WHEN %s = 'completed' THEN CURRENT_TIMESTAMP ELSE NULL END
                )
                RETURNING user_lesson_progress_id;
                """,
                (user_id, lesson_variant_id, current_page_id, status, status),
            )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"user_lesson_progress_id": r[0]})

    # ---------- Telemetry ----------

    @app.route("/api/telemetry/sessions", methods=["POST"])
    def telemetry_start_session():
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        data = request.get_json() or {}
        device_type = (data.get("device_type") or "").strip() or None
        user_agent = request.headers.get("User-Agent") or data.get("user_agent")
        conn = auth_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO tbl_user_session (user_id, device_type, user_agent)
            VALUES (%s, %s, %s)
            RETURNING user_session_id, session_started_timestamp;
            """,
            (user_id, device_type, user_agent),
        )
        r = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        return (
            jsonify(
                {
                    "user_session_id": r[0],
                    "session_started_timestamp": r[1].isoformat() if r[1] else None,
                }
            ),
            201,
        )

    @app.route("/api/telemetry/sessions/<int:session_id>", methods=["PATCH"])
    def telemetry_update_session(session_id):
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        data = request.get_json() or {}
        conn = auth_db()
        cur = conn.cursor()
        fields = ["last_activity_timestamp = CURRENT_TIMESTAMP"]
        vals = []
        if data.get("end_session"):
            fields.append("session_ended_timestamp = CURRENT_TIMESTAMP")
        if "estimated_active_seconds" in data:
            fields.append("estimated_active_seconds = %s")
            vals.append(int(data["estimated_active_seconds"] or 0))
        if "estimated_idle_seconds" in data:
            fields.append("estimated_idle_seconds = %s")
            vals.append(int(data["estimated_idle_seconds"] or 0))
        vals.extend([session_id, user_id])
        cur.execute(
            f"""
            UPDATE tbl_user_session
            SET {", ".join(fields)}
            WHERE user_session_id = %s AND user_id = %s
            RETURNING user_session_id;
            """,
            vals,
        )
        r = cur.fetchone()
        if not r:
            conn.rollback()
            cur.close()
            conn.close()
            return jsonify({"error": "Not found"}), 404
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})

    @app.route("/api/telemetry/events", methods=["POST"])
    def telemetry_post_events():
        claims = get_current_user()
        if not claims:
            return jsonify({"error": "Not authenticated"}), 401
        user_id = claims["user_id"]
        data = request.get_json() or {}
        events = data.get("events")
        if not events or not isinstance(events, list):
            return jsonify({"error": "events array is required"}), 400
        conn = auth_db()
        cur = conn.cursor()
        inserted = 0
        for ev in events:
            if not isinstance(ev, dict):
                continue
            et = (ev.get("event_type") or "").strip()
            if et not in ALLOWED_ACTIVITY_EVENT_TYPES:
                continue
            route_name = (ev.get("route_name") or "").strip() or None
            rot = (ev.get("related_object_type") or "").strip() or None
            roi = ev.get("related_object_id")
            roi = str(roi) if roi is not None else None
            sid = ev.get("user_session_id")
            sid = int(sid) if sid is not None else None
            if sid is not None:
                cur.execute(
                    "SELECT 1 FROM tbl_user_session WHERE user_session_id = %s AND user_id = %s;",
                    (sid, user_id),
                )
                if not cur.fetchone():
                    sid = None
            cur.execute(
                """
                INSERT INTO tbl_user_activity_event (
                  user_id, user_session_id, event_type, route_name, related_object_type, related_object_id
                ) VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (user_id, sid, et, route_name, rot, roi),
            )
            inserted += 1
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"inserted": inserted})
