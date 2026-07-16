"""
itinerary_recommender.py

슬롯(지역, 테마, 여행일수, 동행)이 확정된 뒤,
gilddara.db(attractions, markets)에서 실제로 일정을 뽑아 Day별로 배분하는 모듈.

핵심 아이디어:
- 지역(region): sigungu_name 정확히 일치 우선, 없으면 address LIKE 보조 매칭
- 테마(theme): lcls1_name 카테고리로 매핑 (여러 개 가능)
- 일수(day_count): 하루당 [음식 1 + 테마 관광지 2~3 + (선택)시장 1] 배분
  - 마지막 날 제외하고 숙박(체험) 1건도 추천에 포함 (다일 여행일 때)
- 이미 뽑힌 곳은 같은 일정 내에서 중복 추천하지 않음

이 모듈은 순수 DB 조회 로직이라 LLM 없이 바로 테스트 가능.
슬롯 추출(자연어 -> region/theme/companion/day_count)은 slot_extraction.py에서 담당.
"""
import sqlite3
from dataclasses import dataclass, field
from typing import Optional


# TourAPI lcls1_name 카테고리 목록 (attractions.lcls1_name과 정확히 일치해야 함)
THEME_CATEGORIES = [
    "음식", "문화관광", "숙박", "역사관광", "자연관광",
    "체험관광", "축제/공연/행사", "추천코스", "쇼핑", "레저스포츠",
]

# 사용자 자유 발화 테마 키워드 -> lcls1_name 매핑 (LLM이 매핑 못했을 때의 보조 규칙)
THEME_KEYWORD_FALLBACK = {
    "자연": ["자연관광"], "힐링": ["자연관광", "추천코스"], "휴식": ["자연관광"],
    "역사": ["역사관광"], "유적": ["역사관광"],
    "체험": ["체험관광"], "액티비티": ["레저스포츠", "체험관광"], "레저": ["레저스포츠"],
    "맛집": ["음식"], "음식": ["음식"], "먹거리": ["음식"],
    "문화": ["문화관광"], "전시": ["문화관광"],
    "쇼핑": ["쇼핑"], "축제": ["축제/공연/행사"], "공연": ["축제/공연/행사"],
    "가족": ["체험관광", "자연관광", "문화관광"],
    "나홀로": ["자연관광", "추천코스"],
    "캠핑": ["자연관광", "레저스포츠"],
    "도보": ["자연관광", "역사관광"],
}

DEFAULT_THEMES = ["자연관광", "역사관광", "문화관광", "체험관광"]  # 테마 미상시 기본값
ITEMS_PER_DAY = 3          # 하루당 테마 관광지 개수
INCLUDE_MARKET_EVERY_DAY = True
INCLUDE_FOOD_EVERY_DAY = True


@dataclass
class PlanSlots:
    region: Optional[list] = field(default_factory=list)   # sigungu_name 리스트, 비어있으면 전체
    themes: Optional[list] = field(default_factory=list)   # lcls1_name 리스트
    day_count: int = 1
    companion_type: Optional[str] = None
    raw_theme_text: Optional[str] = None  # LLM이 매핑 실패시 폴백용 원문


def resolve_themes(slots: PlanSlots) -> list:
    """slots.themes가 비어있으면 raw_theme_text 키워드로 폴백 매핑, 그래도 없으면 기본 테마"""
    if slots.themes:
        return [t for t in slots.themes if t in THEME_CATEGORIES]

    if slots.raw_theme_text:
        matched = set()
        for kw, cats in THEME_KEYWORD_FALLBACK.items():
            if kw in slots.raw_theme_text:
                matched.update(cats)
        if matched:
            return list(matched)

    return DEFAULT_THEMES


def _region_filter_sql(region_list: list, address_col: str = "address", sigungu_col: str = None):
    """region_list가 있으면 WHERE 절과 파라미터를 반환, 없으면 (None, [])"""
    if not region_list:
        return None, []
    clauses = []
    params = []
    for r in region_list:
        if sigungu_col:
            clauses.append(f"{sigungu_col} = ?")
            params.append(r)
        clauses.append(f"{address_col} LIKE ?")
        params.append(f"%{r}%")
    return "(" + " OR ".join(clauses) + ")", params


def fetch_candidates(conn: sqlite3.Connection, slots: PlanSlots) -> dict:
    """카테고리별 후보 attractions + markets 조회"""
    themes = resolve_themes(slots)
    cur = conn.cursor()

    result = {"food": [], "theme_spots": [], "lodging": [], "markets": []}

    region_where, region_params = _region_filter_sql(slots.region, sigungu_col="sigungu_name")

    # 1) 음식점
    where = "lcls1_name = ?"
    params = ["음식"]
    if region_where:
        where += f" AND {region_where}"
        params += region_params
    cur.execute(f"SELECT id, name, address, lat, lng FROM attractions WHERE {where}", params)
    result["food"] = cur.fetchall()

    # 2) 테마 관광지 (여러 lcls1_name)
    placeholders = ",".join(["?"] * len(themes))
    where = f"lcls1_name IN ({placeholders})"
    params = list(themes)
    if region_where:
        where += f" AND {region_where}"
        params += region_params
    cur.execute(f"SELECT id, name, address, lat, lng, lcls1_name FROM attractions WHERE {where}", params)
    result["theme_spots"] = cur.fetchall()

    # 3) 숙박
    where = "lcls1_name = ?"
    params = ["숙박"]
    if region_where:
        where += f" AND {region_where}"
        params += region_params
    cur.execute(f"SELECT id, name, address, lat, lng FROM attractions WHERE {where}", params)
    result["lodging"] = cur.fetchall()

    # 4) 시장 (markets 테이블엔 sigungu 컬럼이 없어서 address LIKE만 사용)
    market_where, market_params = _region_filter_sql(slots.region)
    query = "SELECT id, name, address, market_type, lat, lng FROM markets"
    if market_where:
        query += f" WHERE {market_where}"
    cur.execute(query, market_params)
    result["markets"] = cur.fetchall()

    return result


def build_itinerary(conn: sqlite3.Connection, slots: PlanSlots) -> list:
    """
    day_count 만큼 Day별 방문지 리스트를 생성.
    반환 형식: [{"day": 1, "items": [{"type": "food"/"attraction"/"market"/"lodging",
                                       "id":..., "name":..., "address":...}, ...]}, ...]
    """
    candidates = fetch_candidates(conn, slots)

    used_attraction_ids = set()
    used_market_ids = set()

    def pop_unused(pool, used_set, id_index=0, limit=1):
        picked = []
        for row in pool:
            rid = row[id_index]
            if rid in used_set:
                continue
            picked.append(row)
            used_set.add(rid)
            if len(picked) >= limit:
                break
        return picked

    itinerary = []
    for day in range(1, slots.day_count + 1):
        day_items = []

        if INCLUDE_FOOD_EVERY_DAY:
            for row in pop_unused(candidates["food"], used_attraction_ids, limit=1):
                day_items.append({"type": "food", "id": row[0], "name": row[1], "address": row[2]})

        spots = pop_unused(candidates["theme_spots"], used_attraction_ids, limit=ITEMS_PER_DAY)
        for row in spots:
            day_items.append({
                "type": "attraction", "id": row[0], "name": row[1],
                "address": row[2], "category": row[5],
            })

        if INCLUDE_MARKET_EVERY_DAY:
            for row in pop_unused(candidates["markets"], used_market_ids, limit=1):
                day_items.append({"type": "market", "id": row[0], "name": row[1], "address": row[2]})

        # 마지막 날이 아니면 숙박 1건 추천 (1박 이상 여행일 때)
        if day < slots.day_count:
            for row in pop_unused(candidates["lodging"], used_attraction_ids, limit=1):
                day_items.append({"type": "lodging", "id": row[0], "name": row[1], "address": row[2]})

        itinerary.append({"day": day, "items": day_items})

    return itinerary


def save_itinerary(
    conn: sqlite3.Connection,
    user_id: int,
    conversation_id: int,
    title: str,
    start_date: str,
    end_date: str,
    slots: PlanSlots,
    itinerary: list,
) -> int:
    """생성된 일정을 itineraries / itinerary_items 테이블에 저장하고 itinerary_id 반환"""
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO itineraries
           (user_id, conversation_id, title, start_date, end_date, theme, companion_type, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
        (user_id, conversation_id, title, start_date, end_date,
         ",".join(resolve_themes(slots)), slots.companion_type),
    )
    itinerary_id = cur.lastrowid

    for day_plan in itinerary:
        day_number = day_plan["day"]
        for order, item in enumerate(day_plan["items"], start=1):
            attraction_id = item["id"] if item["type"] in ("food", "attraction", "lodging") else None
            market_id = item["id"] if item["type"] == "market" else None
            cur.execute(
                """INSERT INTO itinerary_items
                   (itinerary_id, day_number, attraction_id, market_id, visit_order)
                   VALUES (?, ?, ?, ?, ?)""",
                (itinerary_id, day_number, attraction_id, market_id, order),
            )

    conn.commit()
    return itinerary_id