"""
review_service.py
리뷰 작성/수정/삭제, 신고, 관리자 분석
"""
import sqlite3


def create_review(conn: sqlite3.Connection, user_id, store_id, rating, content, photo=None):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO reviews (user_id, store_id, rating, content, photo, status, created_at)
           VALUES (?, ?, ?, ?, ?, '정상', datetime('now'))""",
        (user_id, store_id, rating, content, photo),
    )
    conn.commit()
    return cur.lastrowid


def update_review(conn: sqlite3.Connection, review_id, user_id, rating=None, content=None):
    cur = conn.cursor()
    fields, params = [], []
    if rating is not None:
        fields.append("rating = ?"); params.append(rating)
    if content is not None:
        fields.append("content = ?"); params.append(content)
    if not fields:
        return
    params += [review_id, user_id]
    cur.execute(f"UPDATE reviews SET {', '.join(fields)} WHERE id = ? AND user_id = ?", params)
    conn.commit()


def delete_review(conn: sqlite3.Connection, review_id, user_id):
    cur = conn.cursor()
    cur.execute("UPDATE reviews SET status = '삭제됨' WHERE id = ? AND user_id = ?", (review_id, user_id))
    conn.commit()


def list_store_reviews(conn: sqlite3.Connection, store_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT id, user_id, rating, content, created_at FROM reviews
           WHERE store_id = ? AND status = '정상' ORDER BY created_at DESC""",
        (store_id,),
    )
    return cur.fetchall()


def list_user_reviews(conn: sqlite3.Connection, user_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT r.id, s.name, r.rating, r.content, r.created_at FROM reviews r
           JOIN stores s ON r.store_id = s.id
           WHERE r.user_id = ? AND r.status != '삭제됨' ORDER BY r.created_at DESC""",
        (user_id,),
    )
    return cur.fetchall()


def report_review(conn: sqlite3.Connection, review_id, reporter_user_id, reason):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO review_reports (review_id, reporter_user_id, reason, status, created_at)
           VALUES (?, ?, ?, '접수', datetime('now'))""",
        (review_id, reporter_user_id, reason),
    )
    cur.execute("UPDATE reviews SET status = '신고됨' WHERE id = ?", (review_id,))
    conn.commit()
    return cur.lastrowid


def analyze_store_reviews(conn: sqlite3.Connection, store_id, good_points, improvement_points):
    """관리자가 리뷰 분석 결과를 입력 (실제 자동분석 대신 수기 입력 버전)"""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO review_analysis (store_id, good_points, improvement_points, analyzed_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (store_id, good_points, improvement_points),
    )
    conn.commit()
    return cur.lastrowid