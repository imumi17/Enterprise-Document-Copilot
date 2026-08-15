from fastapi import APIRouter, Depends

from app.auth.dependencies import ensure_profile, get_current_user
from app.auth.models import CurrentUser

router = APIRouter(tags=["auth"])


@router.get("/me")
async def read_current_user(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    ensure_profile(user)
    return user
