"""
Add tavily_web_search pricing config to database
"""
from app.database import SessionLocal
from app.models.credit_pricing import CreditPricingConfig

def add_tavily_pricing():
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(CreditPricingConfig).filter_by(operation_key="tavily_web_search").first()
        
        if existing:
            print(f"⚠️ tavily_web_search config already exists: {existing.cost_per_unit} credits")
            return
        
        print("🚀 Adding tavily_web_search pricing config...")
        
        # Add tavily_web_search config
        tavily_config = CreditPricingConfig(
            operation_key="tavily_web_search",
            operation_name="Tavily Web Search",
            cost_per_unit=5,
            unit_description="per search",
            description="Credit cost per Tavily web search API call"
        )
        
        db.add(tavily_config)
        db.commit()
        
        print(f"\n✅ Added tavily_web_search pricing config:")
        print(f"   • Operation: {tavily_config.operation_name}")
        print(f"   • Cost: {tavily_config.cost_per_unit} credits per search")
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_tavily_pricing()
