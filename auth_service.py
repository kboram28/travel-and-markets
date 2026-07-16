"""
auth_service.py
회원가입 / 로그인 (일반 사용자, 상인, 관리자)

주의: 데모/학습 목적이라 비밀번호를 단순 해시(sha256)만 적용했습니다.
실제 서비스라면 bcrypt/argon2 같은 전용 라이브러리를 쓰세요.
"""
import hashlib
import sqlite3


def _hash_pw(raw_password: str) -> str:
    return hashlib.sha256(raw_password.encode("utf-8")).hexdigest()


# ---------- 일반 사용자 ----------
def register_user(conn: sqlite3.Connection, username, password, name, phone=None, login_type="local"):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    if cur.fetchone():
        raise ValueError("이미 존재하는 아이디예요.")
    cur.execute(
        """INSERT INTO users (username, password_hash, login_type, name, phone, status, created_at)
           VALUES (?, ?, ?, ?, ?, '활성', datetime('now'))""",
        (username, _hash_pw(password), login_type, name, phone),
    )
    conn.commit()
    return cur.lastrowid


def login_user(conn: sqlite3.Connection, username, password):
    cur = conn.cursor()
    cur.execute("SELECT id, password_hash, name FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row or row[1] != _hash_pw(password):
        raise ValueError("아이디 또는 비밀번호를 확인하세요.")
    return {"user_id": row[0], "name": row[2]}


def social_login(conn: sqlite3.Connection, provider, provider_user_id, name):
    """이미 연동된 계정이면 로그인, 없으면 신규가입 + 연동 (간단 버전)"""
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id FROM social_accounts WHERE provider = ? AND provider_user_id = ?",
        (provider, provider_user_id),
    )
    row = cur.fetchone()
    if row:
        return {"user_id": row[0], "is_new": False}

    cur.execute(
        "INSERT INTO users (login_type, name, status, created_at) VALUES (?, ?, '활성', datetime('now'))",
        (provider, name),
    )
    user_id = cur.lastrowid
    cur.execute(
        """INSERT INTO social_accounts (user_id, provider, provider_user_id, connected_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (user_id, provider, provider_user_id),
    )
    conn.commit()
    return {"user_id": user_id, "is_new": True}


# ---------- 상인 ----------
def register_merchant(conn: sqlite3.Connection, username, password, store_name, category, contact_phone=None):
    cur = conn.cursor()
    cur.execute("SELECT id FROM merchants WHERE username = ?", (username,))
    if cur.fetchone():
        raise ValueError("이미 존재하는 아이디예요.")
    cur.execute(
        """INSERT INTO merchants (username, password_hash, store_name, category, contact_phone,
                                   approval_status, created_at)
           VALUES (?, ?, ?, ?, ?, '승인대기', datetime('now'))""",
        (username, _hash_pw(password), store_name, category, contact_phone),
    )
    conn.commit()
    return cur.lastrowid


def submit_merchant_document(conn: sqlite3.Connection, merchant_id, document_type, file_url):
    """서류 제출/재제출 (이력이 쌓임)"""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO merchant_documents (merchant_id, document_type, file_url, status, submitted_at)
           VALUES (?, ?, ?, '검토중', datetime('now'))""",
        (merchant_id, document_type, file_url),
    )
    conn.commit()
    return cur.lastrowid


def login_merchant(conn: sqlite3.Connection, username, password):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, password_hash, store_name, approval_status FROM merchants WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    if not row or row[1] != _hash_pw(password):
        raise ValueError("아이디 또는 비밀번호를 확인하세요.")
    return {"merchant_id": row[0], "store_name": row[2], "approval_status": row[3]}


# ---------- 관리자 ----------
def login_admin(conn: sqlite3.Connection, username, password):
    cur = conn.cursor()
    cur.execute(
        """SELECT id, password_hash, role, scope_market_id, scope_region_code
           FROM admins WHERE username = ?""",
        (username,),
    )
    row = cur.fetchone()
    if not row or row[1] != _hash_pw(password):
        raise ValueError("아이디 또는 비밀번호를 확인하세요.")
    return {
        "admin_id": row[0], "role": row[2],
        "scope_market_id": row[3], "scope_region_code": row[4],
    }


def create_admin(conn: sqlite3.Connection, username, password, role, scope_market_id=None, scope_region_code=None):
    """전체관리자가 상인회/지자체 관리자 계정을 만들어줄 때 사용"""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO admins (username, password_hash, role, scope_market_id, scope_region_code,
                                status, created_at)
           VALUES (?, ?, ?, ?, ?, '활성', datetime('now'))""",
        (username, _hash_pw(password), role, scope_market_id, scope_region_code),
    )
    conn.commit()
    return cur.lastrowid