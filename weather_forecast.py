import os
import dotenv
import logging
from datetime import datetime

import requests
import psycopg2
from psycopg2.extras import execute_values

# 環境変数ロード
dotenv.load_dotenv(dotenv_path="/opt/weather/.weather_env", override=True)

# APIキー・DB接続情報の取得
API_KEY = os.getenv("OPENWEATHER_API_KEY")
DB_PARAMS = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT"))
}

# 47都道府県の県庁所在地リスト
JAPAN_CITIES = [
    "Sapporo", "Aomori", "Morioka", "Sendai", "Akita", "Yamagata", "Fukushima",
    "Mito", "Utsunomiya", "Maebashi", "Saitama", "Chiba", "Tokyo", "Yokohama",
    "Niigata", "Toyama", "Kanazawa", "Fukui", "Kofu", "Nagano",
    "Gifu", "Shizuoka", "Nagoya", "Tsu",
    "Otsu", "Kyoto", "Osaka", "Kobe", "Nara", "Wakayama",
    "Tottori", "Matsue", "Okayama", "Hiroshima", "Yamaguchi",
    "Tokushima", "Takamatsu", "Matsuyama", "Kochi",
    "Fukuoka", "Saga", "Nagasaki", "Kumamoto", "Oita", "Miyazaki", "Kagoshima", "Naha"
]

# ログ設定
logging.basicConfig(
    filename='/home/post/logs/weather_forecast.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)


def fetch_forecast(city: str) -> dict | None:
    """指定した都市の5日間天気予報データをOpenWeather APIから取得する"""
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city},JP&appid={API_KEY}&units=metric&lang=ja"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        logging.error(f"API error for {city}: {e}")
        return None


def insert_forecast_data(data: dict, city: str) -> None:
    """取得した天気予報データをPostgreSQLデータベースに挿入する"""
    if not data:
        return

    entries = []
    for entry in data.get("list", []):
        # 必要な天気データを抽出
        main = entry.get("main", {})
        weather = entry.get("weather", [{}])[0]
        wind = entry.get("wind", {})
        entries.append((
            city,
            datetime.utcfromtimestamp(entry.get("dt")),
            main.get("temp"),
            main.get("feels_like"),
            main.get("temp_min"),
            main.get("temp_max"),
            main.get("humidity"),
            main.get("pressure"),
            entry.get("clouds", {}).get("all"),
            weather.get("description"),
            weather.get("icon"),
            wind.get("speed"),
            wind.get("deg"),
            int(entry.get("pop", 0.0) * 100),
            entry.get("rain", {}).get("3h", 0.0),
            entry.get("snow", {}).get("3h", 0.0)
        ))

    try:
        with psycopg2.connect(**DB_PARAMS) as conn, conn.cursor() as cur:
            # 一括でデータを挿入
            execute_values(cur, """
                INSERT INTO weather.weather_forecast (
                    city_name, forecast_time, temp, feels_like, temp_min, temp_max,
                    humidity, pressure, clouds, weather_description, icon,
                    wind_speed, wind_deg, pop, rain_mm, snow_mm
                ) VALUES %s
            """, entries)
            conn.commit()
        logging.info(f"Inserted forecast data for {city}")
    except Exception as e:
        logging.error(f"DB error for {city}: {e}")


def delete_old_data() -> None:
    """5日以上前の古い天気予報データをデータベースから削除する"""
    try:
        with psycopg2.connect(**DB_PARAMS) as conn, conn.cursor() as cur:
            cur.execute("""
                DELETE FROM weather.weather_forecast
                WHERE created_at < now() - interval '5 days'
            """)
            deleted = cur.rowcount
            conn.commit()
        logging.info(f"Deleted {deleted} old forecast records.")
    except Exception as e:
        logging.error(f"Error deleting old forecast data: {e}")


if __name__ == "__main__":
    # 各都市について天気予報を取得し、DBに保存
    for city in JAPAN_CITIES:
        if (data := fetch_forecast(city)):
            insert_forecast_data(data, city)

    # 古いデータを削除
    delete_old_data()

