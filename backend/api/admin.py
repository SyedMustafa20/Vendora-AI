from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from services.dashboard_service import get_dashboard_data
from services.conversations_service import get_conversations_page
from services.agent_service import get_agent, update_agent
from schemas.dashboard import DashboardResponse
from schemas.conversations import ConversationsPage
from schemas.agent import AgentConfigResponse, AgentConfigUpdate
from core.jwt import decode_access_token, TokenError

from db.database import get_db
from schemas.admin import (
    AdminRegisterRequest, AdminRegisterResponse,
    AdminLoginRequest, AdminLoginResponse,
    TokenRefreshRequest, TokenRefreshResponse,
    LogoutRequest,
)
from backend.services.admin_registrar import register_admin, AdminAlreadyExistsError
from services.admin_login import login_admin, InvalidPasswordError
from services.token_service import issue_token_pair, refresh_token_pair, revoke_refresh_token

router = APIRouter()

_bearer = HTTPBearer()

def require_auth(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> dict:
    try:
        return decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))


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



@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return get_dashboard_data(db)


@router.get("/conversations", response_model=ConversationsPage)
def list_conversations(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    _: dict = Depends(require_auth),
):
    return get_conversations_page(db, page=page, page_size=page_size)


@router.get("/agent", response_model=AgentConfigResponse)
def get_agent_config(
    db: Session = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    admin_id = auth["admin_id"]
    config = get_agent(db, admin_id)
    if config is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent config not found")
    return AgentConfigResponse(
        id=config.id,
        admin_id=config.admin_id,
        agent_type=config.agent_type,
        agent_behavior_type=config.agent_behavior_type,
        intent_prompt=config.intent_prompt,
        generative_prompt=config.generative_prompt,
        model_name=config.model_name,
        model_version=config.model_version,
        temperature=config.temperature,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )


@router.patch("/agent", response_model=AgentConfigResponse)
def update_agent_config(
    payload: AgentConfigUpdate,
    db: Session = Depends(get_db),
    auth: dict = Depends(require_auth),
):
    admin_id = auth["admin_id"]
    try:
        config = update_agent(db, admin_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return AgentConfigResponse(
        id=config.id,
        admin_id=config.admin_id,
        agent_type=config.agent_type,
        agent_behavior_type=config.agent_behavior_type,
        intent_prompt=config.intent_prompt,
        generative_prompt=config.generative_prompt,
        model_name=config.model_name,
        model_version=config.model_version,
        temperature=config.temperature,
        created_at=config.created_at.isoformat() if config.created_at else None,
        updated_at=config.updated_at.isoformat() if config.updated_at else None,
    )