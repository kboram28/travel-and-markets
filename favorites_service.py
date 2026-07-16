"""
favorites_service.py
여행지/전통시장 찜하기
"""
import sqlite3


def add_favorite(conn: sqlite3.Connection, user_id, attraction_id=None, market_id=None):
    if not attraction_id and not market_id:
        raise ValueError("attraction_id 또는 market_id 중 하나는 있어야 해요.")
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO favorites (user_id, attraction_id, market_id, created_at)
           VALUES (?, ?, ?, datetime('now'))""",
        (user_id, attraction_id, market_id),
    )
    conn.commit()
    return cur.lastrowid


def remove_favorite(conn: sqlite3.Connection, favorite_id, user_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE id = ? AND user_id = ?", (favorite_id, user_id))
    conn.commit()
    return cur.rowcount > 0


def list_favorites(conn: sqlite3.Connection, user_id):
    cur = conn.cursor()
    cur.execute(
        """SELECT f.id, f.attraction_id, a.name, f.market_id, m.name
           FROM favorites f
           LEFT JOIN attractions a ON f.attraction_id = a.id
           LEFT JOIN markets m ON f.market_id = m.id
           WHERE f.user_id = ?
           ORDER BY f.created_at DESC""",
        (user_id,),
    )
    rows = cur.fetchall()
    result = []
    for fid, aid, aname, mid, mname in rows:
        if aid:
            result.append({"favorite_id": fid, "type": "attraction", "id": aid, "name": aname})
        else:
            result.append({"favorite_id": fid, "type": "market", "id": mid, "name": mname})
    return result