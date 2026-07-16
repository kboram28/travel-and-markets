"""
settlement_service.py
기간별 매출 집계 + 정산 내역 생성
"""
import sqlite3

SETTLEMENT_FEE_RATE = 0.05  # 수수료 5% (예시)


def calculate_and_create_settlement(conn: sqlite3.Connection, merchant_id, period_start, period_end):
    """
    해당 기간 '픽업완료'된 예약의 상품 합계를 매출로 잡아 정산 레코드 생성.
    (products.price가 없는 데모 데이터에도 안전하게 동작하도록 NULL은 0으로 처리)
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(COALESCE(p.price, 0) * ri.quantity), 0), COUNT(DISTINCT r.id)
        FROM reservations r
        JOIN stores s ON r.store_id = s.id
        JOIN reservation_items ri ON ri.reservation_id = r.id
        JOIN products p ON ri.product_id = p.id
        WHERE s.merchant_id = ? AND r.status = '픽업완료'
          AND r.pickup_time BETWEEN ? AND ?
        """,
        (merchant_id, period_start, period_end),
    )
    total_sales, reservation_count = cur.fetchone()
    fee = int(total_sales * SETTLEMENT_FEE_RATE)
    settlement_amount = total_sales - fee

    cur.execute(
        """INSERT INTO settlements (merchant_id, period_start, period_end, total_sales, fee,
                                     settlement_amount, status, settled_at)
           VALUES (?, ?, ?, ?, ?, ?, '정산예정', NULL)""",
        (merchant_id, period_start, period_end, total_sales, fee, settlement_amount),
    )
    conn.commit()
    return {
        "settlement_id": cur.lastrowid,
        "total_sales": total_sales,
        "fee": fee,
        "settlement_amount": settlement_amount,
        "reservation_count": reservation_count,
    }


def mark_settlement_completed(conn: sqlite3.Connection, settlement_id):
    cur = conn.cursor()
    cur.execute(
        "UPDATE settlements SET status = '정산완료', settled_at = datetime('now') WHERE id = ?",
        (settlement_id,),
    )
    conn.commit()


def list_merchant_settlements(conn: sqlite3.Connection, merchant_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT id, period_start, period_end, total_sales, fee, settlement_amount, status
           FROM settlements WHERE merchant_id = ? ORDER BY period_start DESC""",
        (merchant_id,),
    )
    return cur.fetchall()