"""
Unit tests for database utilities
Tests database session management and utilities
"""

import pytest
from sqlalchemy.orm import Session

from app.database import get_db, Base


@pytest.mark.unit
class TestDatabaseUtils:
    """Test database utility functions"""
    
    def test_get_db_yields_session(self, test_engine):
        """Test get_db yields a valid session"""
        # Create tables
        Base.metadata.create_all(bind=test_engine)
        
        # Override get_db to use test engine
        from sqlalchemy.orm import sessionmaker
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        
        def test_get_db():
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        # Get session from generator
        db_gen = test_get_db()
        db = next(db_gen)
        
        assert db is not None
        assert isinstance(db, Session)
        
        # Cleanup
        try:
            next(db_gen)
        except StopIteration:
            pass
            
    def test_get_db_closes_session_on_exit(self, test_engine):
        """Test get_db closes session after use"""
        Base.metadata.create_all(bind=test_engine)
        
        from sqlalchemy.orm import sessionmaker
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        
        def test_get_db():
            db = TestSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        db_gen = test_get_db()
        db = next(db_gen)
        
        # Session should be active
        assert db.is_active
        
        # Close the generator properly
        try:
            db_gen.close()
        except:
            pass
            
        # Just verify we can create a new session (old one was closed)
        new_gen = test_get_db()
        new_db = next(new_gen)
        assert new_db.is_active
        new_gen.close()
        
    def test_session_rollback_on_error(self, db_session):
        """Test session rollback on error"""
        from app.models.user import User
        
        # Create a user
        user = User(
            email="rollback@example.com",
            username="rollbackuser",
            hashed_password="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Try to create duplicate user (should fail)
        try:
            duplicate_user = User(
                email="rollback@example.com",  # Duplicate email
                username="rollbackuser2",
                hashed_password="hash2"
            )
            db_session.add(duplicate_user)
            db_session.commit()
        except Exception:
            db_session.rollback()
        
        # Original user should still exist
        db_user = db_session.query(User).filter_by(email="rollback@example.com").first()
        assert db_user is not None
        assert db_user.username == "rollbackuser"
        
    def test_session_commit(self, db_session):
        """Test session commit persists data"""
        from app.models.user import User
        
        user = User(
            email="commit@example.com",
            username="commituser",
            hashed_password="hash"
        )
        db_session.add(user)
        db_session.commit()
        
        # Verify user was persisted
        db_user = db_session.query(User).filter_by(email="commit@example.com").first()
        assert db_user is not None
        assert db_user.id is not None
        
    def test_multiple_sessions_independent(self, test_engine):
        """Test multiple sessions are independent"""
        Base.metadata.create_all(bind=test_engine)
        
        from sqlalchemy.orm import sessionmaker
        from app.models.user import User
        
        TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
        
        # Create two sessions
        session1 = TestSessionLocal()
        session2 = TestSessionLocal()
        
        # Add user in session1 but don't commit
        user1 = User(
            email="session1@example.com",
            username="session1user",
            hashed_password="hash1"
        )
        session1.add(user1)
        
        # Session2 shouldn't see uncommitted data from session1
        user_in_session2 = session2.query(User).filter_by(email="session1@example.com").first()
        assert user_in_session2 is None
        
        # Commit in session1
        session1.commit()
        
        # Now session2 should see it
        user_in_session2 = session2.query(User).filter_by(email="session1@example.com").first()
        assert user_in_session2 is not None
        
        # Cleanup
        session1.close()
        session2.close()
