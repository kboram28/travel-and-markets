"""
coupon_service.py
QR 방문 인증 -> 스탬프 적립 -> 7개 채우면 쿠폰 자동 발급
쿠폰 템플릿은 관리자가 미리 만들어둠
"""
import sqlite3
from datetime import datetime, timedelta

STAMP_GOAL = 7


def qr_checkin(conn: sqlite3.Connection, user_id, store_id):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO qr_checkins (user_id, store_id, checked_at) VALUES (?, ?, datetime('now'))",
        (user_id, store_id),
    )
    conn.commit()
    return cur.lastrowid


def add_stamp(conn: sqlite3.Connection, user_id, market_id, coupon_template_id=None):
    """
    스탬프 1개 적립. 7개 채워지면 쿠폰 자동 발급하고 스탬프 초기화.
    coupon_template_id를 안 넘기면, 그 시장에 등록된 활성 템플릿 중 아무거나 하나 사용.
    """
    cur = conn.cursor()
    cur.execute("SELECT id, stamp_count FROM stamps WHERE user_id = ? AND market_id = ?", (user_id, market_id))
    row = cur.fetchone()

    if row:
        stamp_id, count = row
        count += 1
        cur.execute(
            "UPDATE stamps SET stamp_count = ?, updated_at = datetime('now') WHERE id = ?",
            (count, stamp_id),
        )
    else:
        count = 1
        cur.execute(
            """INSERT INTO stamps (user_id, market_id, stamp_count, updated_at)
               VALUES (?, ?, ?, datetime('now'))""",
            (user_id, market_id, count),
        )

    conn.commit()

    if count >= STAMP_GOAL:
        issued = _issue_coupon_from_stamp(conn, user_id, coupon_template_id)
        # 스탬프 초기화
        cur.execute(
            "UPDATE stamps SET stamp_count = 0, updated_at = datetime('now') WHERE user_id = ? AND market_id = ?",
            (user_id, market_id),
        )
        conn.commit()
        return {"stamp_count": 0, "coupon_issued": True, "coupon_id": issued}

    return {"stamp_count": count, "coupon_issued": False}


def _issue_coupon_from_stamp(conn: sqlite3.Connection, user_id, coupon_template_id=None):
    cur = conn.cursor()
    if coupon_template_id is None:
        cur.execute("SELECT id, valid_days FROM coupon_templates ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if not row:
            raise ValueError("발급 가능한 쿠폰 템플릿이 없어요. 관리자가 먼저 만들어야 해요.")
        coupon_template_id, valid_days = row
    else:
        cur.execute("SELECT valid_days FROM coupon_templates WHERE id = ?", (coupon_template_id,))
        valid_days = cur.fetchone()[0]

    expires_at = (datetime.now() + timedelta(days=valid_days or 180)).isoformat()
    cur.execute(
        """INSERT INTO coupons (user_id, coupon_template_id, issued_at, expires_at, status)
           VALUES (?, ?, datetime('now'), ?, '사용가능')""",
        (user_id, coupon_template_id, expires_at),
    )
    conn.commit()
    return cur.lastrowid


def list_user_coupons(conn: sqlite3.Connection, user_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT c.id, ct.title, ct.discount_content, c.status, c.expires_at
           FROM coupons c JOIN coupon_templates ct ON c.coupon_template_id = ct.id
           WHERE c.user_id = ? ORDER BY c.issued_at DESC""",
        (user_id,),
    )
    return cur.fetchall()


def use_coupon(conn: sqlite3.Connection, coupon_id, user_id):
    cur = conn.cursor()
    cur.execute("SELECT status, expires_at FROM coupons WHERE id = ? AND user_id = ?", (coupon_id, user_id))
    row = cur.fetchone()
    if not row:
        raise ValueError("쿠폰을 찾을 수 없어요.")
    status, expires_at = row
    if status != "사용가능":
        raise ValueError(f"사용할 수 없는 쿠폰이에요 (상태: {status}).")
    if expires_at and expires_at < datetime.now().isoformat():
        cur.execute("UPDATE coupons SET status = '만료' WHERE id = ?", (coupon_id,))
        conn.commit()
        raise ValueError("기간이 만료된 쿠폰이에요.")

    cur.execute(
        "UPDATE coupons SET status = '사용완료', used_at = datetime('now') WHERE id = ?",
        (coupon_id,),
    )
    conn.commit()


# ---------- 관리자: 쿠폰 템플릿 관리 ----------
def create_coupon_template(conn: sqlite3.Connection, admin_id, title, discount_content, valid_days=180):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO coupon_templates (admin_id, title, discount_content, valid_days, created_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (admin_id, title, discount_content, valid_days),
    )
    conn.commit()
    return cur.lastrowid


def list_coupon_templates(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT id, title, discount_content, valid_days FROM coupon_templates")
    return cur.fetchall()