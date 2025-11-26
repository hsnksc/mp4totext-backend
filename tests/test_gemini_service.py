"""
Unit Tests for Gemini Service
Tests AI text enhancement functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.gemini_service import GeminiService, get_gemini_service


class TestGeminiService:
    """Test Gemini AI service"""
    
    def test_service_initialization_with_valid_key(self):
        """Test service initializes with valid API key"""
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "test-api-key"
            
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    service = GeminiService()
                    assert service.api_key == "test-api-key"
                    assert service.model_name == "gemini-2.5-flash"
    
    def test_service_disabled_with_dummy_key(self):
        """Test service is disabled with dummy key"""
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "dummy-key"
            
            service = GeminiService()
            assert service.is_enabled() is False
    
    def test_service_disabled_with_no_key(self):
        """Test service is disabled with no key"""
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = None
            
            service = GeminiService()
            assert service.is_enabled() is False
    
    @pytest.mark.asyncio
    async def test_enhance_text_when_disabled(self):
        """Test enhancement fails when service is disabled"""
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "dummy-key"
            
            service = GeminiService()
            
            with pytest.raises(Exception, match="Gemini service is not enabled"):
                await service.enhance_text("test text")
    
    @pytest.mark.asyncio
    async def test_enhance_text_with_short_text(self):
        """Test enhancement fails with text too short"""
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "test-api-key"
            
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel'):
                    service = GeminiService()
                    service.enabled = True
                    
                    with pytest.raises(ValueError, match="Text is too short"):
                        await service.enhance_text("hi")
    
    @pytest.mark.asyncio
    async def test_enhance_text_success(self):
        """Test successful text enhancement"""
        # Mock Gemini response - text must be a string, not a Mock
        mock_response = Mock()
        mock_response.text = '''
{
    "enhanced_text": "Hello, this is a test.",
    "summary": "Test summary",
    "improvements": ["Punctuation", "Capitalization"],
    "word_count": 5
}
'''
        
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "test-api-key"
            
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel') as mock_model:
                    mock_instance = Mock()
                    # generate_content is sync, not async
                    mock_instance.generate_content = Mock(return_value=mock_response)
                    mock_model.return_value = mock_instance
                    
                    service = GeminiService()
                    service.enabled = True
                    service.model = mock_instance
                    
                    result = await service.enhance_text(
                        "hello this is a test",
                        language="en",
                        include_summary=True
                    )
                    
                    assert result["enhanced_text"] == "Hello, this is a test."
                    assert result["summary"] == "Test summary"
                    assert "Punctuation" in result["improvements"]
                    assert result["word_count"] == 5
                    assert result["language"] == "en"
                    assert result["model_used"] == "gemini-2.5-flash"
    
    @pytest.mark.asyncio
    async def test_enhance_text_with_invalid_json(self):
        """Test enhancement with invalid JSON response"""
        # Mock Gemini response with invalid JSON
        mock_response = Mock()
        mock_response.text = "This is not valid JSON"
        
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "test-api-key"
            
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel') as mock_model:
                    mock_instance = Mock()
                    mock_instance.generate_content = Mock(return_value=mock_response)
                    mock_model.return_value = mock_instance
                    
                    service = GeminiService()
                    service.enabled = True
                    service.model = mock_instance
                    
                    result = await service.enhance_text(
                        "hello this is a test",
                        language="en"
                    )
                    
                    # Should fallback to raw response
                    assert result["enhanced_text"] == "This is not valid JSON"
                    assert result["improvements"] == ["Text formatting and correction"]
    
    @pytest.mark.asyncio
    async def test_summarize_text_success(self):
        """Test successful text summarization"""
        mock_response = Mock()
        mock_response.text = "This is a test summary."
        
        with patch('app.services.gemini_service.get_settings') as mock_settings:
            mock_settings.return_value.GEMINI_API_KEY = "test-api-key"
            
            with patch('google.generativeai.configure'):
                with patch('google.generativeai.GenerativeModel') as mock_model:
                    mock_instance = Mock()
                    mock_instance.generate_content = Mock(return_value=mock_response)
                    mock_model.return_value = mock_instance
                    
                    service = GeminiService()
                    service.enabled = True
                    service.model = mock_instance
                    
                    summary = await service.summarize_text(
                        "This is a long text that needs to be summarized",
                        language="en",
                        max_length=100
                    )
                    
                    assert summary == "This is a test summary."
    
    def test_get_gemini_service_singleton(self):
        """Test get_gemini_service returns singleton"""
        service1 = get_gemini_service()
        service2 = get_gemini_service()
        
        assert service1 is service2
