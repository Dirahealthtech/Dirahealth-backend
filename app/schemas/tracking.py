from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class CheckpointCreate(BaseModel):
    """Schema for creating a tracking checkpoint"""
    status: str
    location: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None

class TrackingUpdate(BaseModel):
    """Schema for updating tracking information"""
    status: Optional[str] = None
    location: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    checkpoint: Optional[CheckpointCreate] = None

class CheckpointResponse(BaseModel):
    """Schema for tracking checkpoint responses"""
    id: int
    status: str
    location: Optional[str] = None
    timestamp: datetime
    description: Optional[str] = None

    class Config:
        from_attributes = True

class TrackingResponse(BaseModel):
    """Schema for tracking responses"""
    id: Optional[int] = None
    order_id: int
    order_number: str
    status: str
    location: Optional[str] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    estimated_delivery: Optional[datetime] = None
    details: Optional[Dict[str, Any]] = None
    checkpoints: List[CheckpointResponse] = []

    class Config:
        from_attributes = True