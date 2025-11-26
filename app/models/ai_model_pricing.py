"""
AI Model Pricing Configuration
Farklı AI modelleri için dinamik fiyatlandırma
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base


class AIModelPricing(Base):
    """
    AI model bazlı kredi fiyatlandırması
    Her model için farklı kredi maliyeti
    """
    __tablename__ = "ai_model_pricing"

    id = Column(Integer, primary_key=True, index=True)
    model_key = Column(String, unique=True, nullable=False, index=True)  # gemini-2.5-flash, gemini-2.5-pro
    model_name = Column(String, nullable=False)  # "Gemini 2.5 Flash"
    provider = Column(String, nullable=False, default="gemini")  # gemini, openai, anthropic
    
    # Fiyatlandırma bilgileri
    credit_multiplier = Column(Float, nullable=False, default=1.0)  # Base operasyona göre çarpan (eski sistem)
    cost_per_1k_chars = Column(Float, nullable=True)  # 1000 karakter başına kredi maliyeti (yeni sistem)
    description = Column(String, nullable=True)  # "Fastest, most balanced model"
    
    # Meta bilgiler
    api_cost_per_1m_input = Column(Float, nullable=True)  # Gerçek API maliyeti (referans)
    api_cost_per_1m_output = Column(Float, nullable=True)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AIModelPricing(model={self.model_key}, multiplier={self.credit_multiplier})>"
