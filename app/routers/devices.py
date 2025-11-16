from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DeviceDTO(BaseModel):
  token: str
  platform: str


@router.post("/")
def register_device(dto: DeviceDTO):
  return {"ok": True}


@router.delete("/{token}")
def delete_device(token: str):
  return {"ok": True}


