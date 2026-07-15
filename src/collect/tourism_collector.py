"""
1) TourAPI(한국관광공사) 호출 - 광주/전남 관광지만
2) 전국전통시장표준데이터 API 호출 - 광주/전남 전통시장만
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERVICE_KEY = os.getenv("SERVICE_KEY")  # TourAPI, 전통시장API 공통으로 사용

TOUR_BASE_URL = "https://apis.data.go.kr/B551011/KorService2"

# TourAPI 지역코드: 광주=5, 전남=38
REGIONS = {"광주": "5", "전남": "38"}


# ---------- 1) 관광지 API 호출 (광주/전남만) ----------
def get_area_based_list(area_code, num_of_rows=10):
    """지역코드로 관광지 목록 가져오기"""
    url = f"{TOUR_BASE_URL}/areaBasedList2"
    params = {
        "serviceKey": SERVICE_KEY,
        "MobileOS": "ETC",
        "MobileApp": "MyApp",
        "_type": "json",
        "areaCode": area_code,
        "numOfRows": num_of_rows,
    }
    res = requests.get(url, params=params)
    data = res.json()
    items = data["response"]["body"]["items"]["item"]
    return items


def get_gwangju_jeonnam_attractions(num_of_rows=10):
    """광주 + 전남 관광지를 합쳐서 반환"""
    all_attractions = []
    for region_name, area_code in REGIONS.items():
        items = get_area_based_list(area_code, num_of_rows)
        for item in items:
            item["_region"] = region_name  # 어느 지역인지 표시
        all_attractions.extend(items)
    return all_attractions


# ---------- 사용 예시 ----------
if __name__ == "__main__":
    print("=== 광주/전남 관광지 ===")
    attractions = get_gwangju_jeonnam_attractions(num_of_rows=5)
    for a in attractions:
        print(f"[{a['_region']}]", a["title"], "-", a["addr1"])
