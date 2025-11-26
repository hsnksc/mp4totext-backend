"""
Unit tests for authentication utilities
Tests password hashing, JWT token creation and verification
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.auth.utils import (
    get_password_hash,
    verify_password,
    create_access_token,
    SECRET_KEY,  # Import the hardcoded secret from utils
    ALGORITHM,   # Import the algorithm
)


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification"""
    
    def test_password_hashing(self):
        """Test password is correctly hashed"""
        password = "Pass123!"  # Shortened for bcrypt 72-byte limit
        hashed = get_password_hash(password)
        
        # Hash should be different from original password
        assert hashed != password
        
        # Hash should start with bcrypt identifier
        assert hashed.startswith("$2b$")
        
    def test_password_verification_success(self):
        """Test correct password verification"""
        password = "Pass123!"  # Shortened for bcrypt 72-byte limit
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        
    def test_password_verification_failure(self):
        """Test incorrect password verification"""
        password = "Pass123!"  # Shortened for bcrypt 72-byte limit
        wrong_password = "Wrong!"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
        
    def test_same_password_different_hashes(self):
        """Test same password produces different hashes (salt)"""
        password = "Pass123!"  # Shortened for bcrypt 72-byte limit
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token creation and verification"""
    
    def test_create_access_token(self):
        """Test JWT access token creation"""
        data = {"sub": "testuser", "email": "test@example.com"}
        token = create_access_token(data)
        
        # Token should be a string
        assert isinstance(token, str)
        
        # Token should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3
        
    def test_create_token_with_expiration(self):
        """Test token with custom expiration"""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires_delta)
        
        # Decode token to check expiration
        decoded = jwt.decode(
            token,
            SECRET_KEY,  # Use hardcoded secret from utils
            algorithms=[ALGORITHM]  # Use hardcoded algorithm from utils
        )
        
        assert "exp" in decoded
        assert "sub" in decoded
        assert decoded["sub"] == "testuser"
        
    def test_decode_valid_token(self):
        """Test decoding of valid token"""
        data = {"sub": "testuser", "email": "test@example.com"}
        token = create_access_token(data)
        
        # Decode and verify
        payload = jwt.decode(
            token,
            SECRET_KEY,  # Use hardcoded secret from utils
            algorithms=[ALGORITHM]  # Use hardcoded algorithm from utils
        )
        
        assert payload is not None
        assert payload["sub"] == "testuser"
        assert payload["email"] == "test@example.com"
        
    def test_decode_expired_token_raises_error(self):
        """Test decoding of expired token raises error"""
        data = {"sub": "testuser"}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-10)
        token = create_access_token(data, expires_delta=expires_delta)
        
        # Should raise JWTError for expired token
        with pytest.raises(JWTError):
            jwt.decode(
                token,
                SECRET_KEY,  # Use hardcoded secret from utils
                algorithms=[ALGORITHM]  # Use hardcoded algorithm from utils
            )
        
    def test_decode_invalid_token_raises_error(self):
        """Test decoding of invalid token raises error"""
        invalid_token = "invalid.token.string"
        
        with pytest.raises(JWTError):
            jwt.decode(
                invalid_token,
                SECRET_KEY,  # Use hardcoded secret from utils
                algorithms=[ALGORITHM]  # Use hardcoded algorithm from utils
            )
        
    def test_decode_token_wrong_secret_raises_error(self):
        """Test decoding with wrong secret fails"""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Try to decode with wrong secret
        with pytest.raises(JWTError):
            jwt.decode(
                token,
                "wrong_secret_key",
                algorithms=[ALGORITHM]  # Use hardcoded algorithm from utils
            )
            
    def test_token_contains_all_claims(self):
        """Test token contains all expected claims"""
        data = {
            "sub": "testuser",
            "email": "test@example.com",
            "is_superuser": False
        }
        token = create_access_token(data)
        
        payload = jwt.decode(
            token,
            SECRET_KEY,  # Use hardcoded secret from utils
            algorithms=[ALGORITHM]  # Use hardcoded algorithm from utils
        )
        
        assert payload["sub"] == "testuser"
        assert payload["email"] == "test@example.com"
        assert payload["is_superuser"] is False
        assert "exp" in payload
