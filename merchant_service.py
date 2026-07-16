"""
merchant_service.py
매장/상품/할인/이벤트/팀 관리 (상인 화면 로직)
"""
import sqlite3


# ---------- 매장 ----------
def create_store(conn: sqlite3.Connection, merchant_id, market_id, name, location_detail=None):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO stores (merchant_id, market_id, name, location_detail, status)
           VALUES (?, ?, ?, ?, '영업')""",
        (merchant_id, market_id, name, location_detail),
    )
    conn.commit()
    return cur.lastrowid


def list_merchant_stores(conn: sqlite3.Connection, merchant_id):
    cur = conn.cursor()
    cur.execute("SELECT id, name, market_id, status FROM stores WHERE merchant_id = ?", (merchant_id,))
    return cur.fetchall()


def update_store_info(conn: sqlite3.Connection, store_id, **fields):
    """기본정보/영업정보/위치 등 수정 (넘긴 필드만 업데이트)"""
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    cur = conn.cursor()
    cur.execute(f"UPDATE stores SET {set_clause} WHERE id = ?", (*fields.values(), store_id))
    conn.commit()


# ---------- 상품 ----------
def add_product(conn: sqlite3.Connection, store_id, name, stock=0, price=None):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO products (store_id, name, stock, price) VALUES (?, ?, ?, ?)",
        (store_id, name, stock, price),
    )
    conn.commit()
    return cur.lastrowid


def list_store_products(conn: sqlite3.Connection, store_id):
    cur = conn.cursor()
    cur.execute("SELECT id, name, stock, price FROM products WHERE store_id = ?", (store_id,))
    return cur.fetchall()


# ---------- 할인/이벤트 ----------
def create_discount(conn: sqlite3.Connection, store_id, discount_rate, target_product_id, start_date, end_date):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO discounts (store_id, discount_rate, target_product_id, start_date, end_date)
           VALUES (?, ?, ?, ?, ?)""",
        (store_id, discount_rate, target_product_id, start_date, end_date),
    )
    conn.commit()
    return cur.lastrowid


def create_event(conn: sqlite3.Connection, store_id, content, participation_method, start_date, end_date):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO events (store_id, content, participation_method, start_date, end_date)
           VALUES (?, ?, ?, ?, ?)""",
        (store_id, content, participation_method, start_date, end_date),
    )
    conn.commit()
    return cur.lastrowid


# ---------- 팀 ----------
def create_team(conn: sqlite3.Connection, team_name, invite_code):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO merchant_teams (team_name, invite_code, created_at) VALUES (?, ?, datetime('now'))",
        (team_name, invite_code),
    )
    conn.commit()
    return cur.lastrowid


def join_team(conn: sqlite3.Connection, merchant_id, invite_code):
    cur = conn.cursor()
    cur.execute("SELECT id FROM merchant_teams WHERE invite_code = ?", (invite_code,))
    row = cur.fetchone()
    if not row:
        raise ValueError("초대코드가 올바르지 않아요.")
    team_id = row[0]
    cur.execute("UPDATE merchants SET team_id = ? WHERE id = ?", (team_id, merchant_id))
    cur.execute(
        "INSERT INTO team_members (team_id, merchant_id, joined_at) VALUES (?, ?, datetime('now'))",
        (team_id, merchant_id),
    )
    conn.commit()
    return team_id


def list_team_members(conn: sqlite3.Connection, team_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT m.id, m.store_name FROM team_members tm
           JOIN merchants m ON tm.merchant_id = m.id
           WHERE tm.team_id = ?""",
        (team_id,),
    )
    return cur.fetchall()


# ---------- 스케줄 ----------
def add_schedule(conn: sqlite3.Connection, merchant_id, date, market_id, status, team_id=None):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO merchant_schedules (merchant_id, team_id, date, market_id, status)
           VALUES (?, ?, ?, ?, ?)""",
        (merchant_id, team_id, date, market_id, status),
    )
    conn.commit()
    return cur.lastrowid