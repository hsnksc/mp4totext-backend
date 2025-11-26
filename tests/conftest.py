"""
Pytest Configuration and Fixtures
Shared test fixtures for all tests
"""

import pytest
import asyncio
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from httpx import AsyncClient
import os

# Set test environment before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.database import Base, get_db
from app.settings import get_settings
from app.models.user import User
from app.auth.utils import get_password_hash


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create test database engine - fresh for each test"""
    # Use in-memory SQLite for tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        echo=False
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a new database session for a test"""
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    
    session = TestingSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """FastAPI test client with database override"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(db_session: Session) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing with database override"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user_data():
    """Test user data - shorter password to avoid bcrypt 72 byte limit"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123!",  # Shorter password
        "full_name": "Test User"
    }


@pytest.fixture
def test_user(db_session: Session, test_user_data):
    """Create a test user in database"""
    user = User(
        email=test_user_data["email"],
        username=test_user_data["username"],
        hashed_password=get_password_hash(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(client: TestClient, test_user, test_user_data):
    """Get authentication headers for test user"""
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# Mock Services
# ============================================================================

@pytest.fixture
def mock_storage():
    """Mock storage service"""
    class MockStorage:
        def upload_file(self, file, file_id):
            return f"test/{file_id}"
        
        def get_file_path(self, file_id):
            return f"test/{file_id}"
        
        def delete_file(self, file_id):
            return True
    
    return MockStorage()


@pytest.fixture
def mock_gemini():
    """Mock Gemini service"""
    class MockGemini:
        def __init__(self):
            self.enabled = True
        
        def is_enabled(self):
            return self.enabled
        
        async def enhance_text(self, text, language="tr", include_summary=True):
            return {
                "enhanced_text": f"Enhanced: {text}",
                "summary": "Test summary" if include_summary else "",
                "improvements": ["Capitalization", "Punctuation"],
                "word_count": len(text.split()),
                "original_length": len(text),
                "enhanced_length": len(text) + 10,
                "model_used": "gemini-2.5-flash",
                "language": language
            }
    
    return MockGemini()


# ============================================================================
# Async Event Loop
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
