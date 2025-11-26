"""
Configuration module for MP4toText
Environment-specific configurations: development, staging, production
"""

from .base import BaseConfig
from .development import DevelopmentConfig
from .staging import StagingConfig
from .production import ProductionConfig
import os

def get_config():
    """
    Get configuration based on ENVIRONMENT variable
    
    Returns:
        Config object (Development/Staging/Production)
    """
    env = os.getenv('ENVIRONMENT', 'development').lower()
    
    config_map = {
        'development': DevelopmentConfig(),
        'dev': DevelopmentConfig(),
        'staging': StagingConfig(),
        'stage': StagingConfig(),
        'production': ProductionConfig(),
        'prod': ProductionConfig(),
    }
    
    config = config_map.get(env, DevelopmentConfig())
    print(f"🔧 Loaded configuration: {config.__class__.__name__}")
    return config

__all__ = ['BaseConfig', 'DevelopmentConfig', 'StagingConfig', 'ProductionConfig', 'get_config']
