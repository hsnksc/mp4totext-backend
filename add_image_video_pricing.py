"""
Add Image and Video Generation Pricing
Migration script to add image and video generation pricing to credit_pricing_configs
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models.credit_pricing import CreditPricingConfig
from app.models.source import Source  # Import to resolve relationships


def add_image_video_pricing():
    """Add image and video generation pricing configs"""
    db = SessionLocal()
    
    try:
        # Image generation pricing configs
        image_configs = [
            {
                "operation_key": "image_generation_sdxl",
                "operation_name": "Görsel Üretimi (SDXL)",
                "cost_per_unit": 2.0,
                "unit_description": "görsel başı",
                "description": "Stable Diffusion XL ile görsel üretimi"
            },
            {
                "operation_key": "image_generation_flux",
                "operation_name": "Görsel Üretimi (FLUX)",
                "cost_per_unit": 5.0,
                "unit_description": "görsel başı",
                "description": "FLUX H100 ile ultra kalite görsel üretimi"
            },
            {
                "operation_key": "image_generation_imagen",
                "operation_name": "Görsel Üretimi (Imagen-4)",
                "cost_per_unit": 8.0,
                "unit_description": "görsel başı",
                "description": "Google Imagen-4 ile fotorealistik görsel üretimi"
            },
        ]
        
        # Video generation pricing configs
        video_configs = [
            {
                "operation_key": "video_generation_base",
                "operation_name": "Video Üretimi (Base)",
                "cost_per_unit": 20.0,
                "unit_description": "video başı",
                "description": "Transkripten otomatik video oluşturma"
            },
            {
                "operation_key": "video_generation_per_segment",
                "operation_name": "Video Segment",
                "cost_per_unit": 2.0,
                "unit_description": "segment başı",
                "description": "Video segment başına ek maliyet"
            },
            {
                "operation_key": "video_tts_narration",
                "operation_name": "Video Seslendirme (TTS)",
                "cost_per_unit": 0.5,
                "unit_description": "dakika başı",
                "description": "OpenAI TTS ile video seslendirme"
            },
        ]
        
        all_configs = image_configs + video_configs
        added = 0
        updated = 0
        
        for config in all_configs:
            existing = db.query(CreditPricingConfig).filter_by(
                operation_key=config["operation_key"]
            ).first()
            
            if existing:
                # Update existing
                existing.operation_name = config["operation_name"]
                existing.cost_per_unit = config["cost_per_unit"]
                existing.unit_description = config["unit_description"]
                existing.description = config["description"]
                existing.is_active = True
                updated += 1
                print(f"📝 Updated: {config['operation_key']}")
            else:
                # Create new
                new_config = CreditPricingConfig(**config, is_active=True)
                db.add(new_config)
                added += 1
                print(f"✅ Added: {config['operation_key']}")
        
        db.commit()
        
        print(f"""
╔════════════════════════════════════════════════════════════╗
║           IMAGE & VIDEO PRICING ADDED                      ║
╠════════════════════════════════════════════════════════════╣
║  Added:    {added} new pricing configs                          ║
║  Updated:  {updated} existing configs                            ║
╚════════════════════════════════════════════════════════════╝
        """)
        
        # List all pricing configs
        print("\n📋 All Pricing Configs:")
        all_prices = db.query(CreditPricingConfig).order_by(CreditPricingConfig.operation_key).all()
        for p in all_prices:
            status = "✅" if p.is_active else "❌"
            print(f"  {status} {p.operation_key}: {p.cost_per_unit} kr/{p.unit_description}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_image_video_pricing()
