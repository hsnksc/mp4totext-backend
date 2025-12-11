"""
Authentication API endpoints
Register, Login, User info, Google OAuth
"""

from datetime import timedelta
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx
import secrets

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.auth.utils import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_current_active_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from app.settings import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

# Also create a router for /api/auth (without v1) for Google callback
oauth_router = APIRouter(prefix="/api/auth", tags=["OAuth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)) -> Any:
    """
    Register new user
    
    - **email**: Valid email address
    - **username**: Unique username (3-50 characters)
    - **password**: Password (min 6 characters)
    - **full_name**: Optional full name
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        if existing_user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_superuser=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)) -> Any:
    """
    Login user and return JWT token
    
    - **username**: Username
    - **password**: Password
    """
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get current logged in user information
    
    Requires: Bearer token in Authorization header
    """
    return current_user


@router.get("/users/test")
async def test_endpoint() -> dict:
    """Test endpoint to verify auth router is working"""
    return {
        "message": "Auth router is working!",
        "endpoints": [
            "POST /api/v1/auth/register - Register new user",
            "POST /api/v1/auth/login - Login user",
            "GET /api/v1/auth/me - Get current user info (requires token)"
        ]
    }


async def require_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency to require superuser/admin privileges
    
    Usage:
        @router.get("/admin/users")
        async def get_all_users(
            current_user: User = Depends(require_superuser),
            db: Session = Depends(get_db)
        ):
            ...
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin access required."
        )
    return current_user


# =============================================================================
# GOOGLE OAUTH ENDPOINTS
# =============================================================================

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google/login")
async def google_login():
    """
    Redirect user to Google OAuth consent screen
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent"
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"
    
    return {"auth_url": auth_url, "state": state}


@oauth_router.get("/google/callback")
async def google_callback(
    code: str = Query(...),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback
    Exchange code for tokens, get user info, create/login user
    """
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured"
        )
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token: {token_response.text}"
            )
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # Get user info from Google
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user info from Google"
            )
        
        google_user = userinfo_response.json()
    
    # Extract user info
    email = google_user.get("email")
    name = google_user.get("name", "")
    google_id = google_user.get("id")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Google"
        )
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user with Google account
        username = email.split("@")[0]
        # Make username unique if needed
        base_username = username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=email,
            username=username,
            full_name=name,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),  # Random password
            is_active=True,
            is_superuser=False,
            credits=10.0  # Welcome bonus for new users
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # Redirect to frontend with token
    frontend_url = "https://gistify.pro"
    redirect_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    
    return RedirectResponse(url=redirect_url)


# =============================================================================
# X (TWITTER) OAUTH 2.0 ENDPOINTS
# =============================================================================

X_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
X_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
X_USERINFO_URL = "https://api.twitter.com/2/users/me"

# Redis client for X OAuth state storage
def get_redis_client():
    """Get Redis client for OAuth state storage"""
    import redis
    redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
    return redis.from_url(redis_url, decode_responses=True)


@router.get("/x/login")
async def x_login():
    """
    Redirect user to X (Twitter) OAuth 2.0 consent screen
    Uses PKCE (Proof Key for Code Exchange) for security
    """
    if not settings.X_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="X (Twitter) OAuth is not configured"
        )
    
    import hashlib
    import base64
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    # Generate PKCE code verifier and challenge
    code_verifier = secrets.token_urlsafe(64)[:128]  # 43-128 characters
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip('=')
    
    # Store state and code_verifier in Redis (expires in 10 minutes)
    try:
        redis_client = get_redis_client()
        redis_client.setex(f"x_oauth_state:{state}", 600, code_verifier)
    except Exception as e:
        print(f"⚠️ Redis not available, using memory fallback: {e}")
        # Fallback to memory (not recommended for production)
        if not hasattr(x_login, '_states'):
            x_login._states = {}
        x_login._states[state] = code_verifier
    
    params = {
        "response_type": "code",
        "client_id": settings.X_CLIENT_ID,
        "redirect_uri": settings.X_REDIRECT_URI,
        "scope": "users.read tweet.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    
    from urllib.parse import urlencode
    auth_url = f"{X_AUTH_URL}?{urlencode(params)}"
    
    return {"auth_url": auth_url, "state": state}


@oauth_router.get("/x/callback")
async def x_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle X (Twitter) OAuth 2.0 callback
    Exchange code for tokens using PKCE, get user info, create/login user
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"X OAuth error: {error}"
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )
    
    # Validate state and get code_verifier from Redis
    code_verifier = None
    try:
        redis_client = get_redis_client()
        code_verifier = redis_client.get(f"x_oauth_state:{state}")
        if code_verifier:
            redis_client.delete(f"x_oauth_state:{state}")
    except Exception as e:
        print(f"⚠️ Redis not available, checking memory fallback: {e}")
        # Fallback to memory
        if hasattr(x_login, '_states'):
            code_verifier = x_login._states.pop(state, None)
    
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter. Please try again."
        )
    
    if not settings.X_CLIENT_ID or not settings.X_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="X OAuth is not configured"
        )
    
    import base64
    
    # Create Basic Auth header
    credentials = f"{settings.X_CLIENT_ID}:{settings.X_CLIENT_SECRET}"
    basic_auth = base64.b64encode(credentials.encode()).decode()
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            X_TOKEN_URL,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic_auth}"
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.X_REDIRECT_URI,
                "code_verifier": code_verifier
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from X: {token_response.text}"
            )
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # Get user info from X
        userinfo_response = await client.get(
            X_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            params={"user.fields": "id,name,username,profile_image_url"}
        )
        
        if userinfo_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get user info from X: {userinfo_response.text}"
            )
        
        x_user_data = userinfo_response.json()
        x_user = x_user_data.get("data", {})
    
    # Extract user info
    x_user_id = x_user.get("id")
    x_username = x_user.get("username")
    x_name = x_user.get("name", "")
    
    if not x_user_id or not x_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User info not provided by X"
        )
    
    # X doesn't provide email, so we use x_username@x.com as placeholder
    # Find user by X username pattern or create new
    placeholder_email = f"{x_username}@x.gistify.local"
    
    user = db.query(User).filter(User.email == placeholder_email).first()
    
    if not user:
        # Also check if username exists
        username = x_username
        base_username = username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=placeholder_email,
            username=username,
            full_name=x_name,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            is_active=True,
            is_superuser=False,
            credits=10.0  # Welcome bonus
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # Redirect to frontend with token
    frontend_url = "https://gistify.pro"
    redirect_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    
    return RedirectResponse(url=redirect_url)
# =============================================================================
# AMAZON OAUTH ENDPOINTS (Login with Amazon)
# =============================================================================

AMAZON_AUTH_URL = "https://www.amazon.com/ap/oa"
AMAZON_TOKEN_URL = "https://api.amazon.com/auth/o2/token"
AMAZON_PROFILE_URL = "https://api.amazon.com/user/profile"

# State cache for Amazon OAuth (in production, use Redis)
amazon_auth_states = {}


@router.get("/amazon/login")
async def amazon_login():
    """
    Redirect user to Amazon OAuth consent screen
    """
    if not settings.AMAZON_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Amazon OAuth is not configured"
        )
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    amazon_auth_states[state] = True
    
    params = {
        "client_id": settings.AMAZON_CLIENT_ID,
        "redirect_uri": settings.AMAZON_REDIRECT_URI,
        "response_type": "code",
        "scope": "profile",
        "state": state
    }
    
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{AMAZON_AUTH_URL}?{query_string}"
    
    return {"auth_url": auth_url, "state": state}


@oauth_router.get("/amazon/callback")
async def amazon_callback(
    code: str = Query(None),
    state: str = Query(None),
    error: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Handle Amazon OAuth callback
    Exchange code for tokens, get user info, create/login user
    """
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amazon OAuth error: {error}"
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )
    
    # Validate state
    if not amazon_auth_states.pop(state, None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    if not settings.AMAZON_CLIENT_ID or not settings.AMAZON_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Amazon OAuth is not configured"
        )
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            AMAZON_TOKEN_URL,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.AMAZON_REDIRECT_URI,
                "client_id": settings.AMAZON_CLIENT_ID,
                "client_secret": settings.AMAZON_CLIENT_SECRET
            }
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from Amazon: {token_response.text}"
            )
        
        tokens = token_response.json()
        access_token = tokens.get("access_token")
        
        # Get user profile from Amazon
        profile_response = await client.get(
            AMAZON_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if profile_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user profile from Amazon"
            )
        
        amazon_user = profile_response.json()
    
    # Extract user info
    email = amazon_user.get("email")
    name = amazon_user.get("name", "")
    amazon_user_id = amazon_user.get("user_id")
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by Amazon"
        )
    
    # Find or create user
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        # Create new user with Amazon account
        username = email.split("@")[0]
        # Make username unique if needed
        base_username = username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = User(
            email=email,
            username=username,
            full_name=name,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),  # Random password
            is_active=True,
            is_superuser=False,
            credits=10.0  # Welcome bonus for new users
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jwt_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    # Redirect to frontend with token
    frontend_url = "https://gistify.pro"
    redirect_url = f"{frontend_url}/auth/callback?token={jwt_token}"
    
    return RedirectResponse(url=redirect_url)
