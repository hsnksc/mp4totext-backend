"""
Credit Pricing Configuration Model
Dinamik fiyatlandırma için veritabanı modeli
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.sql import func
from app.database import Base


class CreditPricingConfig(Base):
    """
    Kredi fiyatlandırma yapılandırması
    Admin panel'den düzenlenebilir
    """
    __tablename__ = "credit_pricing_configs"

    id = Column(Integer, primary_key=True, index=True)
    operation_key = Column(String, unique=True, nullable=False, index=True)
    operation_name = Column(String, nullable=False)
    cost_per_unit = Column(Float, nullable=False)  # Float for fractional credits (0.5, 1.5, etc.)
    unit_description = Column(String, nullable=False)  # "dakika başı", "işlem başı" vs
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<CreditPricingConfig(key={self.operation_key}, cost={self.cost_per_unit})>"
