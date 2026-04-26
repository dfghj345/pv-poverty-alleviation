from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PolicyTable(Base):
    __tablename__ = "policy_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    province: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    price: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    subsidy: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    policy_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    policy_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class WeatherRadiationTable(Base):
    __tablename__ = "weather_radiation_table"
    __table_args__ = (
        UniqueConstraint("latitude", "longitude", "day", "source", name="uq_weather_radiation_business"),
        Index("ix_weather_radiation_lat_lon_day", "latitude", "longitude", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    day: Mapped[date] = mapped_column(Date, nullable=False)

    shortwave_radiation_sum_kwh_m2: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False)
    temperature_mean_c: Mapped[float | None] = mapped_column(Numeric(8, 3), nullable=True)
    precipitation_sum_mm: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    wind_speed_mean_m_s: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    annual_radiation_sum_kwh_m2: Mapped[float | None] = mapped_column(Numeric(12, 6), nullable=True)
    equivalent_hours_h: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)

    source: Mapped[str] = mapped_column(String(50), nullable=False, default="open_meteo")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CityLocationTable(Base):
    __tablename__ = "city_location_table"
    __table_args__ = (
        UniqueConstraint("province", "city", name="uq_city_location_province_city"),
        Index("ix_city_location_province_city", "province", "city"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="city_location_reference")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class PovertyCountyTable(Base):
    __tablename__ = "poverty_county_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    province: Mapped[str] = mapped_column(String(50), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    county: Mapped[str] = mapped_column(String(100), nullable=False)

    population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    income_per_capita_yuan: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    energy_condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)
    adcode: Mapped[str | None] = mapped_column(String(50), nullable=True)

    source: Mapped[str] = mapped_column(String(50), nullable=False, default="poverty_dataset")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class CostTable(Base):
    __tablename__ = "cost_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)

    unit_cost_yuan_per_kw: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    component_price_yuan_per_w: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)

    effective_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="pv_costs")
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class GenerationTable(Base):
    __tablename__ = "generation_table"
    __table_args__ = (
        UniqueConstraint("province", "city", "county", "year", name="uq_generation_region_year"),
        Index("ix_generation_region_year", "province", "city", "county", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_name: Mapped[str] = mapped_column(String(200), nullable=False)
    province: Mapped[str | None] = mapped_column(String(50), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    installed_capacity_kw: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    utilization_hours: Mapped[float | None] = mapped_column(Numeric(10, 3), nullable=True)
    capacity_kw: Mapped[float | None] = mapped_column(Numeric(14, 3), nullable=True)
    annual_generation_kwh: Mapped[float | None] = mapped_column(Numeric(18, 3), nullable=True)
    annual_income_yuan: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="generation")
    remark: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class EnergyPolicyTable(Base):
    __tablename__ = "energy_policy_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str] = mapped_column(String(800), nullable=False, unique=True)
    publish_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    source: Mapped[str] = mapped_column(String(50), nullable=False, default="nea")
    source_url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

