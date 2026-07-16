"""
chatbot_service.py

유저 플로우 문서의 "챗봇" 화면 로직을 그대로 구현:
  사용자 메시지 입력
    -> 정보 추출 및 분석 (동행/지역/기간/테마)
    -> 정보가 충분한가?
         N -> 추가 질문 생성 (부족한 항목 되묻기)
         Y -> 일정 생성 -> 일정 결과 표시
    -> 대화 자동 저장 (chatbot_messages, 왼쪽 목록 = chatbot_conversations)

이 모듈이 실제 백엔드(FastAPI/Flask 등)에서 호출할 진입점 함수는 handle_user_message().
"""
import json
import sqlite3
from datetime import date, timedelta
from typing import Optional

from slot_extraction import (
    call_llm_for_slots,
    merge_slots,
    find_missing_slots,
    generate_followup_question,
    slots_dict_to_plan_slots,
)
from itinerary_recommender import build_itinerary, save_itinerary


def start_conversation(conn: sqlite3.Connection, user_id: int, title: str = "새 대화") -> int:
    """유저 플로우의 '새 대화 생성'에 해당. conversation_id 반환"""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chatbot_conversations (user_id, title, created_at, slots_json) "
        "VALUES (?, ?, datetime('now'), ?)",
        (user_id, title, json.dumps({})),
    )
    conn.commit()
    return cur.lastrowid


def _save_message(conn: sqlite3.Connection, conversation_id: int, sender: str, content: str):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO chatbot_messages (conversation_id, sender, content, created_at) "
        "VALUES (?, ?, ?, datetime('now'))",
        (conversation_id, sender, content),
    )
    conn.commit()


def _load_conversation_history(conn: sqlite3.Connection, conversation_id: int) -> list:
    cur = conn.cursor()
    cur.execute(
        "SELECT sender, content FROM chatbot_messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    )
    rows = cur.fetchall()
    return [{"role": "user" if sender == "user" else "assistant", "content": content} for sender, content in rows]


def _load_saved_slots(conn: sqlite3.Connection, conversation_id: int) -> dict:
    cur = conn.cursor()
    cur.execute("SELECT slots_json FROM chatbot_conversations WHERE id = ?", (conversation_id,))
    row = cur.fetchone()
    if row and row[0]:
        return json.loads(row[0])
    return {}


def _save_slots(conn: sqlite3.Connection, conversation_id: int, slots: dict):
    cur = conn.cursor()
    cur.execute(
        "UPDATE chatbot_conversations SET slots_json = ? WHERE id = ?",
        (json.dumps(slots, ensure_ascii=False), conversation_id),
    )
    conn.commit()


def handle_user_message(
    conn: sqlite3.Connection,
    user_id: int,
    conversation_id: int,
    user_message: str,
    api_key: Optional[str] = None,
) -> dict:
    """
    유저 플로우의 '사용자 메시지 입력' ~ '일정 생성 결과 제공' 전체를 한 번에 처리.

    반환값 예:
      되물어야 할 때:  {"type": "question", "message": "여행 기간이 어떻게 되세요?"}
      일정 완성됐을 때: {"type": "itinerary", "itinerary_id": 12, "days": [...]}
    """
    # 1) 사용자 메시지 저장
    _save_message(conn, conversation_id, "user", user_message)

    # 2) 지금까지의 전체 대화로 슬롯 재추출 (LLM 호출)
    history = _load_conversation_history(conn, conversation_id)
    extracted = call_llm_for_slots(history, api_key=api_key)

    # 3) 이전 턴까지 저장된 슬롯과 병합 (LLM이 이번 턴에 놓친 값은 이전 값 유지)
    previous_slots = _load_saved_slots(conn, conversation_id)
    merged_slots = merge_slots(previous_slots, extracted)
    _save_slots(conn, conversation_id, merged_slots)

    # 4) 정보가 충분한가?
    missing = find_missing_slots(merged_slots)

    if missing:
        question = generate_followup_question(missing)
        _save_message(conn, conversation_id, "bot", question)
        return {"type": "question", "message": question, "slots": merged_slots}

    # 5) 정보 충분 -> 일정 생성
    plan_slots = slots_dict_to_plan_slots(merged_slots)
    itinerary_days = build_itinerary(conn, plan_slots)

    start = date.today()
    end = start + timedelta(days=plan_slots.day_count - 1)
    title = f"{'/'.join(plan_slots.region) if plan_slots.region else '전남광주'} {plan_slots.day_count}일 여행"

    itinerary_id = save_itinerary(
        conn, user_id, conversation_id, title,
        start.isoformat(), end.isoformat(), plan_slots, itinerary_days,
    )

    summary_lines = [f"[{title}] 일정을 만들었어요!"]
    for day in itinerary_days:
        names = ", ".join(item["name"] for item in day["items"])
        summary_lines.append(f"Day {day['day']}: {names}")
    summary_message = "\n".join(summary_lines)

    _save_message(conn, conversation_id, "bot", summary_message)

    return {
        "type": "itinerary",
        "itinerary_id": itinerary_id,
        "title": title,
        "days": itinerary_days,
        "slots": merged_slots,
    }