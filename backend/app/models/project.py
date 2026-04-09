from datetime import date
from sqlalchemy import String, Float, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import DeclarativeBase
from geoalchemy2 import Geometry
from sqlalchemy import Integer
class Base(DeclarativeBase):
    pass

class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="省份")
    electricity_price: Mapped[float] = mapped_column(Float, comment="电价 (元/kWh)")
    subsidy_standard: Mapped[float] = mapped_column(Float, comment="补贴标准 (元/kWh)")
    annual_income: Mapped[float] = mapped_column(Float, nullable=True, default=0.0, comment="年收益(元)")
    annual_generation: Mapped[float] = mapped_column(Float, nullable=True, default=0.0, comment="年发电量(度)")
    farmers_benefited: Mapped[int] = mapped_column(Integer, nullable=True, default=0, comment="惠及农户(户)")
    carbon_reduction: Mapped[float] = mapped_column(Float, nullable=True, default=0.0, comment="减碳量(吨)")
    projects: Mapped[list["Project"]] = relationship(back_populates="policy", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_location_gist", "location", postgresql_using="gist"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    capacity: Mapped[float] = mapped_column(Float, nullable=False, comment="装机容量 (kWp)")
    commissioning_date: Mapped[date] = mapped_column(Date, nullable=False, comment="投产日期")
    location: Mapped[Geometry] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=False,
        comment="经纬度坐标 WGS84",
    )
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id"), nullable=False, index=True)
    policy: Mapped["Policy"] = relationship(back_populates="projects")