from fastapi import APIRouter
from schemas import StatusResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=StatusResponse)
async def health_check() -> StatusResponse:
    return StatusResponse(ok=True, detail="alive")
