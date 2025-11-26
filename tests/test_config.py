"""
Unit tests for application configuration settings
"""

import pytest
import os
from pydantic import ValidationError
from app.settings import Settings, get_settings


@pytest.mark.unit
class TestConfigSettings:
    """Tests for Settings configuration"""
    
    def test_settings_singleton(self):
        """Test that get_settings returns the same instance"""
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
        
    def test_whisper_model_size_validation_valid(self):
        """Test valid Whisper model sizes"""
        valid_sizes = ["tiny", "base", "small", "medium", "large"]
        
        for size in valid_sizes:
            os.environ["WHISPER_MODEL_SIZE"] = size
            settings = Settings()
            assert settings.WHISPER_MODEL_SIZE == size
            
    def test_whisper_model_size_validation_invalid(self):
        """Test invalid Whisper model size raises error"""
        os.environ["WHISPER_MODEL_SIZE"] = "invalid_size"
        
        with pytest.raises(ValidationError):
            Settings()
            
    def test_whisper_device_validation_valid(self):
        """Test valid Whisper devices"""
        valid_devices = ["cpu", "cuda"]
        
        for device in valid_devices:
            # Reset any invalid env vars first
            if "WHISPER_MODEL_SIZE" in os.environ and os.environ["WHISPER_MODEL_SIZE"] == "invalid_size":
                del os.environ["WHISPER_MODEL_SIZE"]
            
            os.environ["WHISPER_DEVICE"] = device
            settings = Settings()
            assert settings.WHISPER_DEVICE == device
            
    def test_whisper_device_validation_invalid(self):
        """Test invalid Whisper device raises error"""
        os.environ["WHISPER_DEVICE"] = "invalid_device"
        
        with pytest.raises(ValidationError):
            Settings()
            
    def test_log_level_validation_valid(self):
        """Test valid log levels"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            # Reset any invalid env vars first
            if "WHISPER_MODEL_SIZE" in os.environ and os.environ["WHISPER_MODEL_SIZE"] == "invalid_size":
                del os.environ["WHISPER_MODEL_SIZE"]
            if "WHISPER_DEVICE" in os.environ and os.environ["WHISPER_DEVICE"] == "invalid_device":
                del os.environ["WHISPER_DEVICE"]
                
            os.environ["LOG_LEVEL"] = level
            settings = Settings()
            assert settings.LOG_LEVEL == level
            
    def test_log_level_validation_invalid(self):
        """Test invalid log level raises error"""
        os.environ["LOG_LEVEL"] = "INVALID"
        
        with pytest.raises(ValidationError):
            Settings()
            
    def test_default_values(self):
        """Test default configuration values"""
        settings = get_settings()
        
        # Check some default values
        assert settings.APP_ENV in ["development", "production", "testing"]
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRATION == 3600  # 1 hour
        assert settings.MAX_UPLOAD_SIZE == 100 * 1024 * 1024  # 100MB (actual default)
        assert settings.RATE_LIMIT_PER_MINUTE == 60
