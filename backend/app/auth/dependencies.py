import httpx
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.models import CurrentUser
from app.config import settings
from app.database.supabase import get_service_role_client

logger = structlog.get_logger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


async def verify_supabase_access_token(access_token: str) -> CurrentUser | None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{settings.supabase_url}/auth/v1/user",
            headers={
                "apikey": settings.supabase_anon_key,
                "Authorization": f"Bearer {access_token}",
            },
        )

    if response.status_code != status.HTTP_200_OK:
        logger.info("auth_token_rejected", status_code=response.status_code)
        return None

    payload = response.json()
    user_id = payload.get("id")
    email = payload.get("email")
    if not user_id or not email:
        return None

    return CurrentUser(id=user_id, email=email)


def ensure_profile(user: CurrentUser) -> None:
    client = get_service_role_client()
    client.table("profiles").upsert(
        {"id": user.id, "email": user.email},
        on_conflict="id",
    ).execute()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )

    user = await verify_supabase_access_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials",
        )

    return user
