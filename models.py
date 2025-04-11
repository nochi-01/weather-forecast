from sqlalchemy import Column, Integer, String, Float, DateTime
from weather_db import Base

class WeatherForecast(Base):
    __tablename__ = "weather_forecast"
    __table_args__ = {"schema": "weather"}

    id = Column(Integer, primary_key=True, index=True)
    city_name = Column(String)
    forecast_time = Column(DateTime)
    temp = Column(Float)
    feels_like = Column(Float)
    temp_min = Column(Float)
    temp_max = Column(Float)
    humidity = Column(Integer)
    pressure = Column(Integer)
    clouds = Column(Integer)
    weather_description = Column(String)
    icon = Column(String)
    wind_speed = Column(Float)
    wind_deg = Column(Integer)
    pop = Column(Integer)
    rain_mm = Column(Float)
    snow_mm = Column(Float)
    created_at = Column(DateTime)
