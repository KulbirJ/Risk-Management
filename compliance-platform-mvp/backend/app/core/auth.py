"""Authentication middleware and utilities with AWS Cognito JWT validation."""

from typing import Optional
from uuid import UUID
from datetime import datetime
from fastapi import Header, HTTPException, status, Depends
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
import requests
from sqlalchemy.orm import Session
import logging

from ..db.database import SessionLocal
from ..models.models import User, Tenant
from ..core.config import settings

logger = logging.getLogger(__name__)

# Cache for Cognito public keys
_jwks_cache = None


class AuthContext:
    """User authentication context."""
    def __init__(self, tenant_id: UUID, user_id: UUID, user: Optional[User] = None):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.user = user


def get_cognito_public_keys():
    """
    Fetch and cache Cognito public keys for JWT validation.
    
    Keys are fetched from:
    https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json
    """
    global _jwks_cache
    
    if _jwks_cache:
        return _jwks_cache
    
    if not settings.cognito_user_pool_id:
        raise ValueError("Cognito User Pool ID not configured")
    
    jwks_url = (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}/.well-known/jwks.json"
    )
    
    try:
        response = requests.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache
    except Exception as e:
        logger.error(f"Failed to fetch Cognito public keys: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service unavailable"
        )


def validate_cognito_token(token: str) -> dict:
    """
    Validate AWS Cognito JWT token and return claims.
    
    Steps:
    1. Decode JWT header to get 'kid' (key ID)
    2. Find matching public key from Cognito JWKS
    3. Verify signature using RSA public key
    4. Verify claims: exp, iss, aud/client_id, token_use
    5. Return decoded claims
    """
    try:
        # Get unverified header to extract key ID
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise JWTError("Missing 'kid' in token header")
        
        # Get Cognito public keys
        jwks = get_cognito_public_keys()
        
        # Find the matching key
        rsa_key = None
        for key in jwks.get('keys', []):
            if key['kid'] == kid:
                rsa_key = {
                    'kty': key['kty'],
                    'kid': key['kid'],
                    'use': key['use'],
                    'n': key['n'],
                    'e': key['e']
                }
                break
        
        if not rsa_key:
            raise JWTError("Public key not found for token")
        
        # Verify and decode token
        issuer = f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/{settings.cognito_user_pool_id}"
        
        claims = jwt.decode(
            token,
            rsa_key,
            algorithms=['RS256'],
            audience=settings.cognito_client_id,
            issuer=issuer,
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_aud': True,
                'verify_iss': True
            }
        )
        
        # Verify token_use claim
        if claims.get('token_use') not in ['access', 'id']:
            raise JWTError("Invalid token_use claim")
        
        return claims
    
    except JWTError as e:
        logger.warning(f"JWT validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error"
        )


def map_cognito_groups_to_roles(cognito_groups: list) -> list:
    """
    Map Cognito user pool groups to application roles.
    
    Cognito Group -> App Roles:
    - Admins -> admin, assessor, reviewer, risk_owner, auditor, viewer
    - Assessors -> assessor, reviewer, viewer
    - Auditors -> auditor, viewer
    - RiskOwners -> risk_owner, viewer
    - Viewers -> viewer
    """
    role_mapping = {
        "Admins": ["admin", "assessor", "reviewer", "risk_owner", "auditor", "viewer"],
        "Assessors": ["assessor", "reviewer", "viewer"],
        "Auditors": ["auditor", "viewer"],
        "RiskOwners": ["risk_owner", "viewer"],
        "Viewers": ["viewer"]
    }
    
    roles = set()
    for group in cognito_groups:
        roles.update(role_mapping.get(group, ["viewer"]))
    
    return list(roles) if roles else ["viewer"]


async def get_current_user_cognito(
    authorization: str = Header(..., description="Bearer {JWT_TOKEN}")
) -> AuthContext:
    """
    Production authentication using AWS Cognito JWT validation.
    
    Extracts and validates JWT token, auto-provisions users on first login.
    """
    # Extract Bearer token
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token = authorization.replace("Bearer ", "")
    
    # Validate token with Cognito
    claims = validate_cognito_token(token)
    
    # Extract user info from claims
    cognito_sub = claims.get("sub")  # Cognito user UUID
    email = claims.get("email")
    cognito_groups = claims.get("cognito:groups", [])
    
    if not cognito_sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims"
        )
    
    # Get or create user in database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.cognito_sub == cognito_sub).first()
        
        if not user:
            # Auto-provision user on first login
            # Note: In production, tenant_id should come from custom claims or be mapped
            # For now, we'll use a default tenant or require it in claims
            tenant_id = claims.get("custom:tenant_id")
            
            if not tenant_id:
                # Fallback: get first tenant or create one (adjust for your requirements)
                tenant = db.query(Tenant).first()
                if not tenant:
                    tenant = Tenant(name="Default Organization", region=settings.aws_region)
                    db.add(tenant)
                    db.commit()
                    db.refresh(tenant)
                tenant_id = tenant.id
            else:
                tenant_id = UUID(tenant_id)
            
            user = User(
                tenant_id=tenant_id,
                cognito_sub=cognito_sub,
                email=email,
                display_name=claims.get("name", email),
                roles=map_cognito_groups_to_roles(cognito_groups),
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Auto-provisioned user: {email}")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return AuthContext(
            tenant_id=user.tenant_id,
            user_id=user.id,
            user=user
        )
    
    finally:
        db.close()


async def get_current_user_basic(
    x_tenant_id: UUID = Header(..., description="Tenant UUID"),
    x_user_id: UUID = Header(..., description="User UUID")
) -> AuthContext:
    """
    Phase 0 MVP: Basic header validation (for local development).
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.id == x_user_id,
            User.tenant_id == x_tenant_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        return AuthContext(
            tenant_id=x_tenant_id,
            user_id=x_user_id,
            user=user
        )
    finally:
        db.close()


# Choose authentication method based on configuration
async def get_current_user_context(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[UUID] = Header(None),
    x_user_id: Optional[UUID] = Header(None)
) -> AuthContext:
    """
    Flexible authentication: use Cognito JWT if configured, otherwise basic headers.
    """
    # If Cognito is configured and authorization header provided, use Cognito
    if settings.cognito_user_pool_id and authorization:
        return await get_current_user_cognito(authorization)
    
    # Fall back to basic header authentication
    if x_tenant_id and x_user_id:
        return await get_current_user_basic(x_tenant_id, x_user_id)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


def require_role(required_role: str):
    """
    Dependency to check if user has required role.
    
    Usage:
        @router.post("/admin-only", dependencies=[Depends(require_role("admin"))])
        def admin_endpoint():
            pass
    """
    async def role_checker(context: AuthContext = Depends(get_current_user_context)):
        if context.user and required_role not in context.user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return context
    
    return role_checker
