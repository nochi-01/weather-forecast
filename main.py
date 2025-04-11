from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from weather_db import SessionLocal
from models import WeatherForecast
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text
import os
from datetime import datetime

app = FastAPI()

# DB接続
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# APIエンドポイント
@app.get("/weather/{city_name}")
def get_weather(city_name: str, db: Session = Depends(get_db)):
    now = datetime.now()

    sql = text("""
        SELECT DISTINCT ON (forecast_time) *
        FROM weather.weather_forecast
        WHERE city_name = :city_name
          AND forecast_time >= :now
        ORDER BY forecast_time, created_at DESC
    """)

    result = db.execute(sql, {
        "city_name": city_name,
        "now": now
    })

    data = [dict(row._mapping) for row in result]

    # 曜日を追加
    weekday_map = ["月", "火", "水", "木", "金", "土", "日"]
    for item in data:
        dt = item["forecast_time"]
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        item["weekday"] = weekday_map[dt.weekday()]

    return data

# index.html設定
frontend_path = os.path.abspath("../weather-frontend")

app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def read_index():
    return FileResponse(f"{frontend_path}/index.html")

