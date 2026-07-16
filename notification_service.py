"""
notification_service.py
알림 발송/조회, 알림 설정, FAQ, 1:1 문의
"""
import sqlite3


# ---------- 알림 ----------
def send_notification(conn: sqlite3.Connection, user_id, type_, content):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO notifications (user_id, type, content, is_read, created_at)
           VALUES (?, ?, ?, 0, datetime('now'))""",
        (user_id, type_, content),
    )
    conn.commit()
    return cur.lastrowid


def list_notifications(conn: sqlite3.Connection, user_id, unread_only=False):
    cur = conn.cursor()
    query = "SELECT id, type, content, is_read, created_at FROM notifications WHERE user_id = ?"
    if unread_only:
        query += " AND is_read = 0"
    query += " ORDER BY created_at DESC"
    cur.execute(query, (user_id,))
    return cur.fetchall()


def mark_notification_read(conn: sqlite3.Connection, notification_id):
    cur = conn.cursor()
    cur.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()


def get_or_create_notification_settings(conn: sqlite3.Connection, user_id):
    cur = conn.cursor()
    cur.execute("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if row:
        return row
    cur.execute(
        """INSERT INTO notification_settings
           (user_id, all_notifications, reservation_alert, review_reply_alert, event_alert, stamp_coupon_alert)
           VALUES (?, 1, 1, 1, 1, 1)""",
        (user_id,),
    )
    conn.commit()
    cur.execute("SELECT * FROM notification_settings WHERE user_id = ?", (user_id,))
    return cur.fetchone()


def update_notification_setting(conn: sqlite3.Connection, user_id, field, value: bool):
    allowed = {"all_notifications", "reservation_alert", "review_reply_alert", "event_alert", "stamp_coupon_alert"}
    if field not in allowed:
        raise ValueError(f"허용되지 않은 설정 항목: {field}")
    cur = conn.cursor()
    cur.execute(f"UPDATE notification_settings SET {field} = ? WHERE user_id = ?", (int(value), user_id))
    conn.commit()


# ---------- FAQ ----------
def create_faq(conn: sqlite3.Connection, category, question, answer):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO faqs (category, question, answer) VALUES (?, ?, ?)",
        (category, question, answer),
    )
    conn.commit()
    return cur.lastrowid


def list_faqs(conn: sqlite3.Connection, category=None):
    cur = conn.cursor()
    if category:
        cur.execute("SELECT id, category, question, answer FROM faqs WHERE category = ?", (category,))
    else:
        cur.execute("SELECT id, category, question, answer FROM faqs")
    return cur.fetchall()


# ---------- 1:1 문의 ----------
def create_inquiry(conn: sqlite3.Connection, user_id, type_, content):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO inquiries (user_id, type, content, status, created_at)
           VALUES (?, ?, ?, '답변대기', datetime('now'))""",
        (user_id, type_, content),
    )
    conn.commit()
    return cur.lastrowid


def answer_inquiry(conn: sqlite3.Connection, inquiry_id, answer):
    cur = conn.cursor()
    cur.execute(
        "UPDATE inquiries SET answer = ?, status = '답변완료' WHERE id = ?",
        (answer, inquiry_id),
    )
    conn.commit()


def list_user_inquiries(conn: sqlite3.Connection, user_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, type, content, status, answer FROM inquiries WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    return cur.fetchall()