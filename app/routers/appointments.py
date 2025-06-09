from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from ..core.dependencies import get_current_user, get_db, RoleChecker
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
techinicians_only = Depends(RoleChecker([UserRole.SERVICE_TECH]))


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
    return await service.get_appointment(appointment_id, current_user)


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


# Technicians endpoints

@router.get("/technician", dependencies=[techinicians_only], response_model=List[AppointmentResponse])
async def get_technicians_appointments(
    service: AppointmentsService = Depends(get_appointment_service),
    current_user: User = Depends(get_current_technician)
):
    """
    List all appointments assigned to the current technician.
    """
    return await service.get_technician_appointment(current_user)


@router.get("/technician/{appointment_id}", dependencies=[techinicians_only], response_model=AppointmentResponse)
async def get_appointment_detail(
    appointment_id: int = Path(..., description="ID of the appointment"),
    service: AppointmentsService = Depends(get_appointment_service),
    current_user: User = Depends(get_current_technician)
):
    """
    Get details of an assigned appointment.
    """
    return await service.get_technician_appointment(appointment_id, current_user)


@router.patch("/technician/{appointment_id}", dependencies=[techinicians_only], response_model=AppointmentResponse)
async def update_appointment_status_or_notes(
    appointment_id: int,
    updates: UpdateScheduledAppointment,
    service: AppointmentsService = Depends(get_appointment_service),
    current_user: User = Depends(get_current_technician)
):
    """
    Update status or notes of your assigned appointment.
    """
    return await service.update_notes_or_status(appointment_id, updates, current_user)
