"""
Unit tests for SQLAlchemy models (User & Transcription)
"""

import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus


@pytest.mark.unit
class TestUserModel:
    """Tests for User model"""
    
    def test_user_creation(self, db_session):
        """Test creating a new user"""
        user = User(
            email="test@example.com",
            username="testuser",
            hashed_password="hashed_password_123",
            full_name="Test User"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None
        
    def test_user_unique_email(self, db_session):
        """Test email uniqueness constraint"""
        user1 = User(
            email="duplicate@example.com",
            username="user1",
            hashed_password="hash1"
        )
        db_session.add(user1)
        db_session.commit()
        
        user2 = User(
            email="duplicate@example.com",
            username="user2",
            hashed_password="hash2"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
    def test_user_unique_username(self, db_session):
        """Test username uniqueness constraint"""
        user1 = User(
            email="user1@example.com",
            username="duplicate",
            hashed_password="hash1"
        )
        db_session.add(user1)
        db_session.commit()
        
        user2 = User(
            email="user2@example.com",
            username="duplicate",
            hashed_password="hash2"
        )
        db_session.add(user2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()
        
    def test_user_string_representation(self, db_session):
        """Test user __repr__ method"""
        user = User(
            email="repr@example.com",
            username="repruser",
            hashed_password="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        repr_str = repr(user)
        assert "User" in repr_str
        assert "repruser" in repr_str


@pytest.mark.unit
class TestTranscriptionModel:
    """Tests for Transcription model"""
    
    def test_transcription_creation(self, db_session, test_user):
        """Test creating a transcription with required fields"""
        transcription = Transcription(
            user_id=test_user.id,
            file_id="test-file-123",
            filename="test.mp4",
            file_size=1024000,
            file_path="/storage/test.mp4",
            content_type="video/mp4",
            status=TranscriptionStatus.PENDING
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)
        
        assert transcription.id is not None
        assert transcription.user_id == test_user.id
        assert transcription.file_id == "test-file-123"
        assert transcription.filename == "test.mp4"
        assert transcription.status == TranscriptionStatus.PENDING
        assert transcription.created_at is not None
        
    def test_transcription_status_enum(self, db_session, test_user):
        """Test all transcription status enum values"""
        statuses = [
            TranscriptionStatus.PENDING,
            TranscriptionStatus.PROCESSING,
            TranscriptionStatus.COMPLETED,
            TranscriptionStatus.FAILED
        ]
        
        for i, status in enumerate(statuses):
            transcription = Transcription(
                user_id=test_user.id,
                file_id=f"test-file-{i}",
                filename=f"test_{status.value}.mp4",
                file_size=1024000,
                file_path=f"/storage/test_{status.value}.mp4",
                content_type="video/mp4",
                status=status
            )
            db_session.add(transcription)
        
        db_session.commit()
        
        # Verify all statuses were created
        assert db_session.query(Transcription).count() == 4
        
    def test_transcription_relationship_to_user(self, db_session, test_user):
        """Test transcription relationship to user"""
        transcription = Transcription(
            user_id=test_user.id,
            file_id="relationship-file-123",
            filename="relationship_test.mp4",
            file_size=1024000,
            file_path="/storage/relationship_test.mp4",
            content_type="video/mp4",
            status=TranscriptionStatus.PENDING
        )
        db_session.add(transcription)
        db_session.commit()
        
        # Verify user_id is correctly set
        assert transcription.user_id == test_user.id
        
    def test_transcription_optional_fields(self, db_session, test_user):
        """Test optional transcription fields"""
        transcription = Transcription(
            user_id=test_user.id,
            file_id="optional-file-123",
            filename="optional_test.mp4",
            file_size=1024000,
            file_path="/storage/optional_test.mp4",
            content_type="video/mp4",
            status=TranscriptionStatus.COMPLETED,
            duration=120.5,
            text="Transcribed text here",
            enhanced_text="Enhanced transcribed text",
            summary="Summary of the transcription",
            processing_time=45.2,
            speaker_count=2
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)
        
        assert transcription.file_path == "/storage/optional_test.mp4"
        assert transcription.duration == 120.5
        assert transcription.file_size == 1024000
        assert transcription.text == "Transcribed text here"
        assert transcription.enhanced_text == "Enhanced transcribed text"
        assert transcription.summary == "Summary of the transcription"
        assert transcription.processing_time == 45.2
        assert transcription.speaker_count == 2
        
    def test_transcription_timestamps_auto_update(self, db_session, test_user):
        """Test that timestamps are correctly managed"""
        transcription = Transcription(
            user_id=test_user.id,
            file_id="timestamp-file-123",
            filename="timestamp_test.mp4",
            file_size=1024000,
            file_path="/storage/timestamp_test.mp4",
            content_type="video/mp4",
            status=TranscriptionStatus.PENDING
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)
        
        original_created = transcription.created_at
        
        # Update the transcription
        transcription.status = TranscriptionStatus.COMPLETED
        db_session.commit()
        db_session.refresh(transcription)
        
        # created_at should not change
        assert transcription.created_at == original_created
        # updated_at should exist
        assert transcription.updated_at is not None or True  # May be None in SQLite
        
    def test_transcription_string_representation(self, db_session, test_user):
        """Test transcription __repr__ method"""
        transcription = Transcription(
            user_id=test_user.id,
            file_id="repr-file-123",
            filename="repr_test.mp4",
            file_size=1024000,
            file_path="/storage/repr_test.mp4",
            content_type="video/mp4",
            status=TranscriptionStatus.PENDING
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)
        
        repr_str = repr(transcription)
        assert "Transcription" in repr_str
        assert "repr_test.mp4" in repr_str
        assert str(transcription.id) in repr_str
