from fastapi import APIRouter

# The auth agent adds the endpoints from contracts/openapi.yaml (/auth/*).
router = APIRouter(prefix="/auth", tags=["auth"])
