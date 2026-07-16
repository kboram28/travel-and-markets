"""
이미 전처리되어 저장된 CSV(data/processed/)를 읽어서
SQLite DB(gilddara.db)에 넣는 스크립트

전제: attractions.csv, markets.csv가 이미 전처리 완료된 상태로
      data/processed/ 폴더에 있음 (EDA 노트북에서 이미 만들어둠)

실행: 프로젝트 루트에서 python src/collect/db_loader.py
"""
import sqlite3
import os
import pandas as pd

# 프로젝트 루트 기준 경로 (이 파일은 src/collect/ 안에 있으므로 두 단계 위로)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "schema_sqlite.sql")
DB_PATH = os.path.join(PROJECT_ROOT, "gilddara.db")
ATTRACTIONS_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "attractions.csv")
MARKETS_CSV = os.path.join(PROJECT_ROOT, "data", "processed", "markets.csv")


def main():
    print("1) 전처리된 CSV 불러오는 중...")
    df_attractions = pd.read_csv(ATTRACTIONS_CSV, encoding="utf-8-sig")
    df_markets = pd.read_csv(MARKETS_CSV, encoding="utf-8-sig")
    print(f"   -> attractions {len(df_attractions)}건, markets {len(df_markets)}건")

    # attractions.csv에 혹시 'region'처럼 DB 테이블에 없는 컬럼이 남아있으면 제거
    df_attractions = df_attractions.drop(columns=["region"], errors="ignore")

    # markets.csv의 items가 문자열로 저장되어 있으면 그대로,
    # 만약 파이썬 리스트 형태(예: "['농산물', '수산물']")로 저장되어 있으면 세미콜론 문자열로 변환
    if df_markets["items"].dtype == object and df_markets["items"].str.startswith("[").any():
        df_markets["items"] = df_markets["items"].apply(
            lambda x: ";".join(eval(x)) if isinstance(x, str) and x.startswith("[") else x
        )

    # has_restroom/has_parking이 True/False(문자열 또는 불리언)로 되어있으면 0/1로 변환
    for col in ["has_restroom", "has_parking"]:
        if col in df_markets.columns:
            df_markets[col] = df_markets[col].astype(bool).astype(int)

    print("2) SQLite DB 생성 중...")
    conn = sqlite3.connect(DB_PATH)
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        conn.executescript(f.read())
    print(f"   -> {DB_PATH} 생성 완료")

    print("3) 데이터 삽입 중...")
    df_attractions.to_sql("attractions", conn, if_exists="append", index=False)
    df_markets.to_sql("markets", conn, if_exists="append", index=False)
    conn.commit()
    print("   -> attractions, markets 테이블 삽입 완료")

    # 확인
    print("\n확인:")
    print(pd.read_sql("SELECT COUNT(*) as cnt FROM attractions", conn))
    print(pd.read_sql("SELECT COUNT(*) as cnt FROM markets", conn))

    conn.close()
    print("\n완료!")


if __name__ == "__main__":
    main()