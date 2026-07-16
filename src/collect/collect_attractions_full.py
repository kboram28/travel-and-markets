"""
전남/광주 관광지 '전체' 데이터 수집 -> 코드 매핑 적용 -> CSV 저장 스크립트

이 스크립트는:
1) tourism_collector.py의 get_gwangju_jeonnam_attractions_all()로
   광주(5) + 전남(38) 전체 관광지를 페이지 끝까지 순회하며 수집
   (contentTypeId를 지정하지 않으므로 관광지/문화시설/축제행사/여행코스/
    레포츠/숙박/쇼핑/음식점 등 모든 콘텐츠 타입 포함)
2) lcls_mapping.json (이미 만들어둔 분류체계 코드-이름 매핑표)을 이용해
   cat1/cat2/cat3 코드를 이름으로 변환 (API를 매번 다시 호출하지 않도록
   build_full_lcls_mapping()이 아니라 기존 json 파일을 재사용)
3) build_full_sigungu_mapping()으로 시군구 코드를 이름으로 변환
4) schema_sqlite.sql의 attractions 테이블 컬럼에 맞춰 정리 후
   data/processed/attractions.csv 로 저장
   (이후 db_loader.py를 그대로 실행하면 DB에 적재됩니다)

실행 위치: 프로젝트 루트에서
    python src/collect/collect_attractions_full.py

사전 준비:
    - 프로젝트 루트에 .env 파일 (SERVICE_KEY=디코딩된_인증키)
    - 프로젝트 루트에 lcls_mapping.json 존재
    - pip install requests python-dotenv pandas

주의:
    - TourAPI는 발급받은 키의 일일 호출 한도가 있습니다(보통 개발계정 1,000회/일).
      광주+전남 전체 + 시군구 매핑을 합치면 페이지 수에 따라 호출 수가 꽤 될 수 있으니,
      한도 초과 시 다음날 이어서 실행하거나 한도를 늘려야 할 수 있습니다.
    - 아래 REQUEST_DELAY_SEC 로 호출 사이 간격을 두어 과도한 연속 호출을 피합니다.
"""
import os
import sys
import json
import time

import pandas as pd

# src/collect 안에서 실행되는 tourism_collector.py를 import
sys.path.insert(0, os.path.dirname(__file__))
from tourism_collector import (  # noqa: E402
    get_area_based_list_all,
    build_full_sigungu_mapping,
    REGIONS,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LCLS_MAPPING_PATH = os.path.join(PROJECT_ROOT, "lcls_mapping.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "processed")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "attractions.csv")
RAW_BACKUP_PATH = os.path.join(OUTPUT_DIR, "attractions_raw_backup.json")

REQUEST_DELAY_SEC = 0.3  # 페이지 호출 사이 딜레이 (API 부하/한도 보호용)


def load_lcls_mapping() -> dict:
    with open(LCLS_MAPPING_PATH, encoding="utf-8") as f:
        return json.load(f)


def collect_all_regions_with_delay() -> list:
    """REGIONS(광주/전남) 전체를 페이지 delay를 주면서 수집"""
    all_items = []
    for region_name, area_code in REGIONS.items():
        print(f"   - {region_name}({area_code}) 수집 시작...")
        page_no = 1
        num_of_rows = 100
        region_items = []
        while True:
            # get_area_based_list_all은 내부에서 전체 페이지를 도므로,
            # 여기서는 진행상황 로그를 위해 직접 페이지 단위로 호출하는 대신
            # 딜레이가 필요하면 아래처럼 래핑해서 사용합니다.
            items = get_area_based_list_all(area_code, num_of_rows=num_of_rows)
            region_items.extend(items)
            break  # get_area_based_list_all이 이미 전체 페이지를 순회함
        for item in region_items:
            item["_region"] = region_name
        print(f"     -> {len(region_items)}건")
        all_items.extend(region_items)
        time.sleep(REQUEST_DELAY_SEC)
    return all_items


def map_row(item: dict, lcls_map: dict, sigungu_map: dict) -> dict:
    area_code = str(item.get("areacode", "") or "")
    sigungu_code = str(item.get("sigungucode", "") or "")
    sigungu_key = f"{area_code}_{sigungu_code}" if area_code and sigungu_code else None

    return {
        "content_id": item.get("contentid"),
        "name": item.get("title"),
        "address": item.get("addr1"),
        "image": item.get("firstimage"),
        "category": item.get("contenttypeid"),
        "lcls1_name": lcls_map.get(item.get("cat1"), item.get("cat1")),
        "lcls2_name": lcls_map.get(item.get("cat2"), item.get("cat2")),
        "lcls3_name": lcls_map.get(item.get("cat3"), item.get("cat3")),
        "area_code": area_code,
        "sigungu_name": sigungu_map.get(sigungu_key, sigungu_code),
        # TourAPI 기준 mapy=위도(lat), mapx=경도(lng)
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
        "tel": item.get("tel"),
        # db_loader.py에서 drop(errors="ignore") 처리되는 참고용 컬럼
        "region": item.get("_region"),
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("1) 시군구 코드 매핑 생성 중...")
    sigungu_map = build_full_sigungu_mapping()
    print(f"   -> {len(sigungu_map)}개 매핑 완료")

    print("2) lcls(분류체계) 매핑 로드 중...")
    lcls_map = load_lcls_mapping()
    print(f"   -> {len(lcls_map)}개 코드 로드 완료")

    print("3) 광주+전남 전체 관광지 수집 중... (전체 콘텐츠 타입, 시간이 걸릴 수 있습니다)")
    raw_items = collect_all_regions_with_delay()
    print(f"   -> 총 {len(raw_items)}건 수집")

    # 원본 raw 응답 백업 (수집 재실행 없이 매핑 로직만 다시 돌리고 싶을 때 사용)
    with open(RAW_BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(raw_items, f, ensure_ascii=False)
    print(f"   -> 원본 백업 저장: {RAW_BACKUP_PATH}")

    print("4) 데이터 정리 및 매핑 적용 중...")
    rows = [map_row(item, lcls_map, sigungu_map) for item in raw_items]
    df = pd.DataFrame(rows)

    before = len(df)
    df = df.drop_duplicates(subset=["content_id"])
    print(f"   -> content_id 기준 중복 제거: {before}건 -> {len(df)}건")

    df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
    print(f"5) 저장 완료: {OUTPUT_PATH} ({len(df)}건)")
    print("\n다음 단계: python src/collect/db_loader.py 를 실행해서 DB에 적재하세요.")


if __name__ == "__main__":
    main()