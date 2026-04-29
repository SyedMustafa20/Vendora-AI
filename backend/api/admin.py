from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

# Add these imports at the top
from services.dashboard_service import get_dashboard_data
from schemas.dashboard import DashboardResponse
from core.jwt import decode_access_token as verify_token  # You'll need to use this for auth


from db.database import get_db
from schemas.admin import (
    AdminRegisterRequest, AdminRegisterResponse,
    AdminLoginRequest, AdminLoginResponse,
    TokenRefreshRequest, TokenRefreshResponse,
    LogoutRequest,
)
from services.admin_registrar import register_admin, AdminAlreadyExistsError
from services.admin_login import login_admin, InvalidPasswordError
from services.token_service import issue_token_pair, refresh_token_pair, revoke_refresh_token
from core.jwt import TokenError

router = APIRouter()


@router.post(
    "/register",
    response_model=AdminRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_admin_endpoint(
    payload: AdminRegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        admin = register_admin(db, payload.username, payload.password)
    except AdminAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return AdminRegisterResponse(
        id=admin.id, user_id=admin.user_id, username=admin.username
    )


@router.post("/login", response_model=AdminLoginResponse)
def login_admin_endpoint(
    payload: AdminLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        admin = login_admin(db, payload.username, payload.password)
    except InvalidPasswordError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    tokens = issue_token_pair(admin)
    return AdminLoginResponse(
        id=admin.id,
        user_id=admin.user_id,
        username=admin.username,
        **tokens,
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token_endpoint(
    payload: TokenRefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        tokens = refresh_token_pair(payload.refresh_token, db)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return TokenRefreshResponse(**tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_endpoint(payload: LogoutRequest):
    revoke_refresh_token(payload.refresh_token)



# Add this endpoint to the router
@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    authorization: str = Depends(verify_token),  # Add auth header check
):
    """
    Get complete dashboard data in one call.
    
    Returns:
    - stats: total_conversations, total_messages, total_users
    - intent_distribution: count per intent type
    - messages_per_day: daily agent messages (30 days)
    - recent_conversations: activity feed
    """
    return get_dashboard_data(db)