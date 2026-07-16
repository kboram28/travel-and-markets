"""
reservation_service.py
물건 예약 (사용자) + 예약 처리 (상인)
"""
import sqlite3


def create_reservation(conn: sqlite3.Connection, user_id, store_id, pickup_time, items: list):
    """
    items: [{"product_id": 1, "quantity": 2}, ...]
    한 상점 + 한 픽업시간 = 예약 1건, 그 안에 품목 여러 개
    """
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO reservations (user_id, store_id, pickup_time, status, created_at)
           VALUES (?, ?, ?, '확인대기', datetime('now'))""",
        (user_id, store_id, pickup_time),
    )
    reservation_id = cur.lastrowid

    for item in items:
        cur.execute(
            "INSERT INTO reservation_items (reservation_id, product_id, quantity) VALUES (?, ?, ?)",
            (reservation_id, item["product_id"], item["quantity"]),
        )
    conn.commit()
    return reservation_id


def list_user_reservations(conn: sqlite3.Connection, user_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT r.id, s.name, r.pickup_time, r.status
           FROM reservations r JOIN stores s ON r.store_id = s.id
           WHERE r.user_id = ? ORDER BY r.created_at DESC""",
        (user_id,),
    )
    return cur.fetchall()


def list_store_reservations(conn: sqlite3.Connection, store_id, status=None):
    cur = conn.cursor()
    query = "SELECT id, user_id, pickup_time, status FROM reservations WHERE store_id = ?"
    params = [store_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    cur.execute(query, params)
    return cur.fetchall()


def update_reservation_status(conn: sqlite3.Connection, reservation_id, new_status, rejection_reason=None):
    """상인이 수락(준비중)/거절/픽업완료 처리"""
    cur = conn.cursor()
    cur.execute(
        "UPDATE reservations SET status = ?, rejection_reason = ? WHERE id = ?",
        (new_status, rejection_reason, reservation_id),
    )
    conn.commit()


def cancel_reservation(conn: sqlite3.Connection, reservation_id, user_id):
    """확인대기 상태일 때만 취소 가능"""
    cur = conn.cursor()
    cur.execute("SELECT status FROM reservations WHERE id = ? AND user_id = ?", (reservation_id, user_id))
    row = cur.fetchone()
    if not row:
        raise ValueError("예약을 찾을 수 없어요.")
    if row[0] != "확인대기":
        raise ValueError("확인대기 상태에서만 취소할 수 있어요.")
    cur.execute("UPDATE reservations SET status = '취소' WHERE id = ?", (reservation_id,))
    conn.commit()