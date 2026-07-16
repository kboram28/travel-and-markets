"""
admin_service.py
상인 승인, 공지사항, 권한(역할/범위)별 실시간 통계 조회
"""
import sqlite3


# ---------- 상인 승인 ----------
def approve_merchant(conn: sqlite3.Connection, merchant_id):
    cur = conn.cursor()
    cur.execute("UPDATE merchants SET approval_status = '승인' WHERE id = ?", (merchant_id,))
    cur.execute(
        "UPDATE merchant_documents SET status = '승인' WHERE merchant_id = ? AND status = '검토중'",
        (merchant_id,),
    )
    conn.commit()


def reject_merchant(conn: sqlite3.Connection, merchant_id, reason):
    cur = conn.cursor()
    cur.execute("UPDATE merchants SET approval_status = '반려' WHERE id = ?", (merchant_id,))
    cur.execute(
        """UPDATE merchant_documents SET status = '반려', rejection_reason = ?
           WHERE merchant_id = ? AND status = '검토중'""",
        (reason, merchant_id),
    )
    conn.commit()


def list_pending_merchants(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT id, store_name, category, created_at FROM merchants WHERE approval_status = '승인대기'")
    return cur.fetchall()


# ---------- 공지사항 ----------
def create_notice(conn: sqlite3.Connection, admin_id, title, content, expires_at=None):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO notices (admin_id, title, content, expires_at, created_at)
           VALUES (?, ?, ?, ?, datetime('now'))""",
        (admin_id, title, content, expires_at),
    )
    conn.commit()
    return cur.lastrowid


def list_notices(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute("SELECT id, title, content, created_at FROM notices ORDER BY created_at DESC")
    return cur.fetchall()


# ---------- 권한(역할/범위)별 실시간 통계 ----------
def get_scoped_stats(conn: sqlite3.Connection, admin: dict):
    """
    admin = {"role": "전체관리자"/"상인회"/"지자체", "scope_market_id": ..., "scope_region_code": ...}
    역할에 따라 조건을 다르게 걸어서 실시간 집계.
    """
    cur = conn.cursor()
    role = admin.get("role")

    base_reservation_q = """
        SELECT COUNT(*) FROM reservations r
        JOIN stores s ON r.store_id = s.id
        WHERE date(r.pickup_time) = date('now')
    """
    base_review_q = "SELECT COUNT(*), AVG(rating) FROM reviews r JOIN stores s ON r.store_id = s.id WHERE r.status = '정상'"
    base_merchant_q = "SELECT COUNT(*) FROM merchants m JOIN stores s ON s.merchant_id = m.id"

    params_reservation, params_review, params_merchant = [], [], []

    if role == "상인회":
        base_reservation_q += " AND s.market_id = ?"
        base_review_q += " AND s.market_id = ?"
        base_merchant_q += " WHERE s.market_id = ?"
        params_reservation.append(admin["scope_market_id"])
        params_review.append(admin["scope_market_id"])
        params_merchant.append(admin["scope_market_id"])
    elif role == "지자체":
        base_reservation_q += " JOIN markets mk ON s.market_id = mk.id AND mk.sigungu_code = ?"
        base_review_q += " JOIN markets mk ON s.market_id = mk.id AND mk.sigungu_code = ?"
        base_merchant_q += " JOIN markets mk ON s.market_id = mk.id WHERE mk.sigungu_code = ?"
        params_reservation.append(admin["scope_region_code"])
        params_review.append(admin["scope_region_code"])
        params_merchant.append(admin["scope_region_code"])
    # 전체관리자는 조건 추가 없음

    today_pickup_count = cur.execute(base_reservation_q, params_reservation).fetchone()[0]
    review_count, avg_rating = cur.execute(base_review_q, params_review).fetchone()
    merchant_count = cur.execute(base_merchant_q, params_merchant).fetchone()[0]

    pending_reports = cur.execute(
        "SELECT COUNT(*) FROM review_reports WHERE status = '접수'"
    ).fetchone()[0]
    pending_merchant_approval = cur.execute(
        "SELECT COUNT(*) FROM merchants WHERE approval_status = '승인대기'"
    ).fetchone()[0] if role != "상인회" else None

    return {
        "role": role,
        "today_pickup_count": today_pickup_count,
        "review_count": review_count,
        "avg_rating": round(avg_rating, 2) if avg_rating else None,
        "merchant_count": merchant_count,
        "pending_reports": pending_reports,
        "pending_merchant_approval": pending_merchant_approval,
    }