from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.project import Base

COLUMN_MAPPING = {
    "省份": "province",
    "城市": "city",
    "年份": "year",
    "PV(光伏装机量,万千瓦)": "pv_installed_capacity_wan_kw",
    "Income(人均可支配收入,元)": "disposable_income_per_capita_yuan",
    "Health(人均医疗支出,元)": "healthcare_expenditure_per_capita_yuan",
    "UR_Ratio(城乡收入比)": "urban_rural_income_ratio",
    "Mortality(总死亡率,‰)": "mortality_per_mille",
    "PM25(年均浓度,μg/m³)": "pm25_annual_avg_ug_per_m3",
    "GDP(地区生产总值,亿元)": "gdp_100m_yuan",
}

UPSERT_COLUMNS = (
    "province",
    "city",
    "year",
    "pv_installed_capacity_wan_kw",
    "disposable_income_per_capita_yuan",
    "healthcare_expenditure_per_capita_yuan",
    "urban_rural_income_ratio",
    "mortality_per_mille",
    "pm25_annual_avg_ug_per_m3",
    "gdp_100m_yuan",
    "source_file",
    "source_workbook",
    "source_sheet",
    "source_row_number",
)

COMPARISON_COLUMNS = UPSERT_COLUMNS


class PanelData(Base):
    __tablename__ = "panel_data"
    __table_args__ = (
        UniqueConstraint("data_hash", name="uq_panel_data_data_hash"),
        UniqueConstraint("province", "city", "year", name="uq_panel_data_province_city_year"),
        Index("idx_panel_data_province_year", "province", "year"),
        Index("idx_panel_data_city_year", "city", "year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    data_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    province: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    pv_installed_capacity_wan_kw: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    disposable_income_per_capita_yuan: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    healthcare_expenditure_per_capita_yuan: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    urban_rural_income_ratio: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    mortality_per_mille: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    pm25_annual_avg_ug_per_m3: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    gdp_100m_yuan: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)

    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    source_workbook: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_sheet: Mapped[str] = mapped_column(String(128), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
