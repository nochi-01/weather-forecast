import requests
import psycopg2
import logging
import dotenv
import os
from datetime import datetime

# .weather_env から環境変数を読み込み
dotenv.load_dotenv(dotenv_path="/opt/weather/.weather_env", override=True)

# APIキーとDB接続情報の取得
API_KEY = os.getenv("OPENWEATHER_API_KEY")
DB_PARAMS = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': int(os.getenv("DB_PORT"))
}

# 47都道府県の県庁所在地
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

# ログ出力設定
logging.basicConfig(
    filename='/home/post/logs/weather_forecast.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

# OpenWeather APIから5日間予報を取得する
def fetch_forecast(city):
    url = f"https://api.openweathermap.org/data/2.5/forecast?q={city},JP&appid={API_KEY}&units=metric&lang=ja"
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return res.json(), city
    except Exception as e:
        logging.error(f"API error for {city}: {e}")
        return None

# データベースへ予報データを挿入する
def insert_forecast_data(data, city):
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()

        # 3時間ごとの予報データを処理
        for entry in data["list"]:
            forecast_time = datetime.utcfromtimestamp(entry["dt"])
            temp = entry["main"]["temp"]
            feels_like = entry["main"]["feels_like"]
            temp_min = entry["main"]["temp_min"]
            temp_max = entry["main"]["temp_max"]
            humidity = entry["main"]["humidity"]
            pressure = entry["main"]["pressure"]
            clouds = entry["clouds"]["all"]
            weather_description = entry["weather"][0]["description"]
            icon = entry["weather"][0]["icon"]
            wind_speed = entry["wind"]["speed"]
            wind_deg = entry["wind"].get("deg")
            pop = int(entry.get("pop", 0.0) * 100)
            rain_mm = entry.get("rain", {}).get("3h", 0.0)
            snow_mm = entry.get("snow", {}).get("3h", 0.0)

            # データ挿入処理
            cur.execute("""
                INSERT INTO weather.weather_forecast (
                    city_name, forecast_time, temp, feels_like, temp_min, temp_max,
                    humidity, pressure, clouds, weather_description, icon,
                    wind_speed, wind_deg, pop, rain_mm, snow_mm
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                city, forecast_time, temp, feels_like, temp_min, temp_max,
                humidity, pressure, clouds, weather_description, icon,
                wind_speed, wind_deg, pop, rain_mm, snow_mm
            ))

        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Inserted forecast data for {city}")
    except Exception as e:
        logging.error(f"DB error for {city}: {e}")

# 5日以上前の古いデータを削除する
def delete_old_data():
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM weather.weather_forecast
            WHERE created_at < now() - interval '5 days';
        """)
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Deleted {deleted} old forecast records.")
    except Exception as e:
        logging.error(f"Error deleting old forecast data: {e}")

# 全都市の予報取得→DB保存→古いデータ削除
if __name__ == "__main__":
    for city in JAPAN_CITIES:
        result = fetch_forecast(city)
        if result:
            data, city_name = result
            insert_forecast_data(data, city_name)

    delete_old_data()
