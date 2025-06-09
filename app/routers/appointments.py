from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_current_user, get_current_technician, get_db, RoleChecker
from ..enums import UserRole
from ..models import Appointment, User
from ..schemas.appointments import (
    AppointmentResponse,
    UpdateScheduledAppointment,
    ScheduleAppointment,
)
from ..services.appointments_service import AppointmentsService


router = APIRouter()
customers_only = Depends(RoleChecker[UserRole.CUSTOMER])


async def get_appointment_service(db: AsyncSession = Depends(get_db)) -> AppointmentsService:
    """
    Dependency function that provides an instance of AppointmentsService.
    This function retrieves a database session using dependency injection and returns
    an AppointmentsService object initialized with the provided asynchronous database session.

    Args:
        db (AsyncSession): The asynchronous database session, injected by FastAPI's Depends.

    Returns:
        AppointmentsService: An instance of the AppointmentsService initialized with the given database session.
    """

    return AppointmentsService(db)


@router.post("/schedule-appointment", dependencies=[customers_only], response_model=List[AppointmentResponse], status_code=status.HTTP_201_CREATED)
async def book_appointment(
    appointment_data: ScheduleAppointment,
    current_user: User = Depends(get_current_user),
    service: AppointmentsService = Depends(get_appointment_service),
):
    """
    Schedule an appointment for a service.

    - Validates service existence and availability.
    - Assigns current user as customer.
    """

    return await service.create_appointment(appointment_data, current_user)


@router.get("/", dependencies=[customers_only], response_model=List[AppointmentResponse])
async def get_my_appointments(
    current_user: User = Depends(get_current_user),
    service: AppointmentsService = Depends(get_appointment_service),
):
    """
    Retrieve all appointments for the current user.
    """
    return await service.get_all_appointments(current_user)


@router.get("/{appointment_id}", dependencies=[customers_only], response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int = Path(..., description="ID of the appointment"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a single appointment by ID if owned by current user.
    """
    appointment = await db.get(Appointment, appointment_id)
    if not appointment or appointment.customer_id != current_user.id:
        return []
    return appointment


@router.put("/{appointment_id}", dependencies=[customers_only], response_model=AppointmentResponse)
async def update_appointment(
    data: UpdateScheduledAppointment,
    appointment_id: int = Path(..., description="ID of the appointment"),
    current_user: User = Depends(get_current_user),
    service: AppointmentsService = Depends(get_appointment_service),
):
    """
    Update appointment details such as time, notes, or technician.

    Only allowed if appointment belongs to current user and is not completed.
    """
    return await service.update_scheduled_appointment(appointment_id, data, current_user)


@router.delete("/{appointment_id}", dependencies=[customers_only], status=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int = Path(..., description="ID of the appointment"),
    current_user: User = Depends(get_current_user),
    service: AppointmentsService = Depends(get_appointment_service),
):
    """
    Delete an appointment if it exists and if the current user scheduled the appointment.
    """
    return await service.delete_scheduled_appointment(appointment_id, current_user)
