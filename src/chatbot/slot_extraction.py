"""
slot_extraction.py

사용자와의 챗봇 대화(누적 메시지)에서
날짜(기간)/지역/동행/테마 슬롯을 추출하고,
부족하면 되물을 질문을 생성하는 모듈.

OpenAI Chat Completions API의 function calling으로
자유 발화를 구조화된 JSON으로 뽑아낸다.

사전 준비:
    pip install openai
    환경변수 OPENAI_API_KEY 설정

주의: 이 파일은 실제 GPT API를 호출하는 부분이라
     이 대화 환경(샌드박스)에서 실행/테스트는 안 해봤습니다.
     (openai.com 도메인 접근 권한이 없어서 여기선 호출 자체가 불가능해요)
     API 키를 넣고 로컬에서 직접 실행/디버깅 해주세요.
"""
import os
import json
from typing import Optional

from itinerary_recommender import PlanSlots, THEME_CATEGORIES

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


MODEL_NAME = "gpt-4o"  # 실제 사용할 모델명으로 교체해서 사용하세요 (예: gpt-4o-mini 등)

# DB의 실제 sigungu_name 목록 (attractions 테이블 기준, 필요시 DB에서 동적으로 가져오도록 교체 가능)
KNOWN_REGIONS = [
    "강진군", "고흥군", "곡성군", "광양시", "구례군", "나주시", "담양군", "목포시",
    "무안군", "보성군", "순천시", "신안군", "여수시", "영광군", "영암군", "완도군",
    "장성군", "장흥군", "진도군", "함평군", "해남군", "화순군",
    "광산구", "남구", "동구", "북구", "서구",  # 광주
]

# OpenAI function calling 스키마 (JSON Schema, "parameters" 키 사용)
SLOT_EXTRACTION_FUNCTION = {
    "name": "extract_travel_slots",
    "description": "사용자 발화에서 여행 일정 계획에 필요한 정보를 추출한다. 언급되지 않은 항목은 넣지 않는다.",
    "parameters": {
        "type": "object",
        "properties": {
            "day_count": {
                "type": "integer",
                "description": "여행 일수. '1박2일'이면 2, '당일치기'면 1, '3일'이면 3.",
            },
            "region": {
                "type": "array",
                "items": {"type": "string", "enum": KNOWN_REGIONS},
                "description": "언급된 시/군/구. 목록에 없는 지역명이 나오면 비워둔다.",
            },
            "themes": {
                "type": "array",
                "items": {"type": "string", "enum": THEME_CATEGORIES},
                "description": "사용자가 원하는 여행 테마를 아래 카테고리 중에서 가장 가까운 것으로 매핑. "
                               "정확히 안 맞으면 비워두고 raw_theme_text에 원문만 남긴다.",
            },
            "raw_theme_text": {
                "type": "string",
                "description": "테마 관련 사용자의 원래 발화 (themes로 명확히 매핑 안 될 때 폴백용)",
            },
            "companion_type": {
                "type": "string",
                "description": "동행 유형 원문 그대로 (예: 가족, 연인, 친구, 혼자, 부모님)",
            },
        },
    },
}

MISSING_SLOT_QUESTIONS = {
    "day_count": "여행 기간이 어떻게 되세요? (예: 당일치기, 1박2일, 2박3일)",
    "region": "어느 지역으로 가고 싶으세요? (예: 여수, 순천, 담양, 광주 등)",
    "companion_type": "누구와 함께 가시나요? (예: 가족, 연인, 친구, 혼자)",
    "themes": "어떤 테마의 여행을 원하세요? (예: 자연/힐링, 역사탐방, 맛집투어, 액티비티 등)",
}

REQUIRED_SLOTS = ["day_count", "region", "companion_type", "themes"]


def call_llm_for_slots(conversation_messages: list, api_key: Optional[str] = None) -> dict:
    """
    conversation_messages: [{"role": "user"/"assistant", "content": "..."}]
    -> 누적 대화 전체를 다시 넣어서 슬롯을 재추출 (매턴 최신 상태로 갱신)
    """
    if OpenAI is None:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다. pip install openai")

    client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    system_prompt = (
        "너는 전남/광주 지역 여행 일정 챗봇의 정보 추출기다. "
        "지금까지의 대화 전체를 보고 extract_travel_slots 함수를 반드시 호출해서 "
        "현재까지 파악된 정보를 최신 상태로 채워라. 언급 안 된 항목은 비워둔다."
    )

    messages = [{"role": "system", "content": system_prompt}] + conversation_messages

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        tools=[{"type": "function", "function": SLOT_EXTRACTION_FUNCTION}],
        tool_choice={"type": "function", "function": {"name": "extract_travel_slots"}},
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        return {}
    return json.loads(tool_calls[0].function.arguments)


def merge_slots(previous: dict, new: dict) -> dict:
    """새로 추출된 슬롯으로 기존 슬롯을 갱신 (새 값이 있으면 덮어씀, 리스트는 새 값이 비어있지 않으면 교체)"""
    merged = dict(previous)
    for key, value in new.items():
        if value in (None, "", []):
            continue
        merged[key] = value
    return merged


def find_missing_slots(slots: dict) -> list:
    missing = []
    for key in REQUIRED_SLOTS:
        val = slots.get(key)
        if key == "themes":
            # themes 또는 raw_theme_text 중 하나라도 있으면 충족으로 봄
            if not val and not slots.get("raw_theme_text"):
                missing.append(key)
        elif not val:
            missing.append(key)
    return missing


def generate_followup_question(missing_slots: list) -> str:
    """부족한 슬롯 중 우선순위가 가장 높은 하나만 되묻는다 (여러 개 한꺼번에 묻지 않음)"""
    priority_order = ["day_count", "region", "companion_type", "themes"]
    for key in priority_order:
        if key in missing_slots:
            return MISSING_SLOT_QUESTIONS[key]
    return "여행 계획에 대해 조금 더 말씀해 주시겠어요?"


def slots_dict_to_plan_slots(slots: dict) -> PlanSlots:
    return PlanSlots(
        region=slots.get("region", []),
        themes=slots.get("themes", []),
        day_count=slots.get("day_count", 1),
        companion_type=slots.get("companion_type"),
        raw_theme_text=slots.get("raw_theme_text"),
    )