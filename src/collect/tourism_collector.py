"""
TourAPI(한국관광공사) 호출 담당 모듈
- 관광지 목록 수집 (지역기반, 전체 페이지 순회)
- 분류체계(lclsSystm) 코드-이름 매핑
- 시군구 코드-이름 매핑
"""
import os
import requests
from dotenv import load_dotenv

# 이 파일(src/collect/tourism_collector.py)의 위치를 기준으로 프로젝트 루트를 찾아
# .env를 로드한다. 실행 위치(cwd)가 어디든(프로젝트 루트에서 실행하든,
# notebooks/에서 실행하든, src/collect/ 안에서 실행하든) 항상 같은 .env를 찾는다.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
load_dotenv(_ENV_PATH)

SERVICE_KEY = os.getenv("SERVICE_KEY")
TOUR_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"

if not SERVICE_KEY:
    print(f"[경고] SERVICE_KEY를 찾지 못했습니다. .env 파일 위치를 확인하세요: {_ENV_PATH}")


def _safe_json(res: requests.Response, context: str = ""):
    """API 응답이 JSON이 아닐 때 원인을 바로 알 수 있도록 원본 응답을 출력하고 에러를 다시 던진다."""
    try:
        return res.json()
    except ValueError:
        print(f"[API 응답 파싱 실패] {context}")
        print(f"  status_code: {res.status_code}")
        print(f"  url: {res.url}")
        print(f"  응답 앞부분: {res.text[:300]}")
        raise

# 광주=5, 전남=38
REGIONS = {"광주": "5", "전남": "38"}


# ---------- 1) 관광지 목록 수집 ----------
def get_area_based_list_all(area_code, content_type_id=None, num_of_rows=100):
    """지역기반 관광정보를 페이지 끝까지 순회하며 전체 가져오기"""
    all_items = []
    page_no = 1
    while True:
        url = f"{TOUR_BASE_URL}/areaBasedList2"
        params = {
            "serviceKey": SERVICE_KEY,
            "MobileOS": "ETC",
            "MobileApp": "MyApp",
            "_type": "json",
            "areaCode": area_code,
            "numOfRows": num_of_rows,
            "pageNo": page_no,
        }
        if content_type_id:
            params["contentTypeId"] = content_type_id

        res = requests.get(url, params=params)
        data = _safe_json(res, f"areaBasedList2 (area_code={area_code}, page={page_no})")
        body = data["response"]["body"]

        items = body.get("items", {})
        items = items.get("item", []) if isinstance(items, dict) else []
        if not items:
            break

        all_items.extend(items)
        page_no += 1

        if len(items) < num_of_rows:
            break

    return all_items


def get_gwangju_jeonnam_attractions_all():
    """광주 + 전남 전체 관광지 가져오기"""
    all_attractions = []
    for region_name, area_code in REGIONS.items():
        items = get_area_based_list_all(area_code)
        for item in items:
            item["_region"] = region_name
        all_attractions.extend(items)
    return all_attractions


# ---------- 2) 분류체계(lclsSystm) 코드-이름 매핑 ----------
def get_lcls_codes(lcls1=None, lcls2=None, num_of_rows=100):
    """
    분류체계 코드-이름 조회
    - 인자 없이 호출 -> 대분류 전체
    - lcls1만 -> 중분류
    - lcls1 + lcls2 -> 소분류
    """
    url = f"{TOUR_BASE_URL}/lclsSystmCode2"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "MyApp",
        "_type": "json",
        "numOfRows": num_of_rows,
    }
    if lcls1:
        params["lclsSystm1"] = lcls1
    if lcls2:
        params["lclsSystm2"] = lcls2

    res = requests.get(url, params=params)
    data = _safe_json(res, f"lclsSystmCode2 (lcls1={lcls1}, lcls2={lcls2})")

    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") != "0000":
        raise RuntimeError(f"API 에러: {header.get('resultCode')} - {header.get('resultMsg')}")

    items = data["response"]["body"]["items"]["item"]
    return {item["code"]: item["name"] for item in items}


def build_full_lcls_mapping():
    """대분류 -> 중분류 -> 소분류 전체 코드-이름 매핑표 생성"""
    full_map = {}
    lcls1_map = get_lcls_codes()
    full_map.update(lcls1_map)

    for lcls1_code in lcls1_map:
        lcls2_map = get_lcls_codes(lcls1=lcls1_code)
        full_map.update(lcls2_map)

        for lcls2_code in lcls2_map:
            lcls3_map = get_lcls_codes(lcls1=lcls1_code, lcls2=lcls2_code)
            full_map.update(lcls3_map)

    return full_map


# ---------- 3) 시군구 코드-이름 매핑 ----------
def get_sigungu_map(area_code):
    """특정 광역지역(area_code)의 시군구 코드-이름 목록 조회"""
    url = f"{TOUR_BASE_URL}/areaCode2"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "MyApp",
        "_type": "json",
        "areaCode": area_code,
        "numOfRows": 100,
    }
    res = requests.get(url, params=params)
    data = _safe_json(res, f"areaCode2 (area_code={area_code})")
    items = data["response"]["body"]["items"]["item"]
    return {item["code"]: item["name"] for item in items}


def build_full_sigungu_mapping():
    """광주+전남 시군구 코드-이름 매핑표 (지역코드_시군구코드 형태로 합성 키 사용)"""
    sigungu_full_map = {}
    for area_code in REGIONS.values():
        sigungu_map = get_sigungu_map(area_code)
        for code, name in sigungu_map.items():
            sigungu_full_map[f"{area_code}_{code}"] = name
    return sigungu_full_map