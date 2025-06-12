from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Dict

from ..enums import AppointmentStatus, PaymentStatus, LocationType


class AppointmentBase(BaseModel):
    service_id: int
    product_id: Optional[int] = None
    technician_id: Optional[int] = None
    scheduled_date: datetime
    status: Optional[AppointmentStatus] = AppointmentStatus.PENDING
    notes: Optional[Dict] = None
    location_type: LocationType
    location_address: Optional[Dict] = None
    payment_status: Optional[PaymentStatus] = PaymentStatus.PENDING
    payment_amount: Optional[float] = None
    payment_transaction_id: Optional[str] = None
    payment_method: Optional[str] = None
    payment_date: Optional[datetime] = None
    reminders: Optional[List[Dict]] = None


class ScheduleAppointment(AppointmentBase):
    pass


class UpdateScheduledAppointment(AppointmentBase):
    pass


class AppointmentResponse(AppointmentBase):
    id: int
    end_time: datetime
    customer_id: int

    class Config:
        orm_mode = True
