"""Auth0 authentication module for inventory.ai."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt import PyJWKClient
from typing import Optional
import requests
from functools import lru_cache

from shared.config import settings


# HTTP Bearer token security scheme
token_auth_scheme = HTTPBearer(auto_error=False)


@lru_cache()
def get_jwks_client() -> PyJWKClient:
    """Get cached JWKS client for Auth0."""
    jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    return PyJWKClient(jwks_url)


def verify_token(token: str) -> dict:
    """
    Verify and decode Auth0 JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        HTTPException: If token is invalid
    """
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[settings.auth0_algorithms],
            audience=settings.auth0_api_audience,
            issuer=f"https://{settings.auth0_domain}/"
        )
        
        return payload
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid audience",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidIssuerError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid issuer",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(token_auth_scheme)
) -> dict:
    """
    Dependency that requires valid Auth0 authentication.
    
    Use this dependency on endpoints that need protection.
    
    Args:
        credentials: HTTP Bearer credentials
        
    Returns:
        Decoded token payload with user info
        
    Raises:
        HTTPException: If no token or invalid token
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = credentials.credentials
    payload = verify_token(token)
    
    return payload


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(token_auth_scheme)
) -> Optional[dict]:
    """
    Dependency that optionally validates Auth0 authentication.
    
    Use this for endpoints that work with or without auth.
    
    Args:
        credentials: HTTP Bearer credentials (optional)
        
    Returns:
        Decoded token payload or None if no token
    """
    if credentials is None:
        return None
    
    try:
        token = credentials.credentials
        payload = verify_token(token)
        return payload
    except HTTPException:
        return None


class Auth0User:
    """Represents an authenticated Auth0 user."""
    
    def __init__(self, payload: dict):
        self.payload = payload
        self.user_id = payload.get("sub")
        self.email = payload.get("email")
        self.permissions = payload.get("permissions", [])
    
    def has_permission(self, permission: str) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions


async def get_current_user(
    payload: dict = Depends(require_auth)
) -> Auth0User:
    """
    Get the current authenticated user.
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        Auth0User object
    """
    return Auth0User(payload)
