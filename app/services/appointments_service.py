from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums import UserRole
from ..models import Appointment, Service, User
from ..schemas import ScheduleAppointment, UpdateScheduledAppointment


class AppointmentsService:
    """
    Service class for managing appointment-related operations.
    This class provides asynchronous methods to create, retrieve, update, and delete appointments
    for users. It interacts with the database using an asynchronous session and ensures that
    appointments are managed in the context of the current authenticated user.
    Attributes:
        db (AsyncSession): The asynchronous database session used for database operations.
    Methods:
        _get_service(service_id: int):
            Asynchronously retrieves a Service object by its ID.
        get_all_appointments(current_user: User):
            Retrieves all appointments associated with the current user.
        get_appointment(appointment_id: int, current_user: User) -> Appointment:
            Retrieves a specific appointment by its ID for the current user.
        create_appointment(data: ScheduleAppointment, current_user: User) -> Appointment:
            Creates a new appointment for the current user.
        update_appointment(appointment_id: int, data: UpdateScheduledAppointment, current_user: User):
            Updates an existing appointment with the provided data for the current user.
        delete_appointment(appointment_id: int, current_user) -> None:
            Deletes an appointment by its ID if it belongs to the current user.
    """

    def __init__(self, db: AsyncSession):
        self.db = db


    async def _get_service(self, service_id: int):
        """
        Asynchronously retrieves a Service object from the database by its ID.

        Args:
            service_id (int): The unique identifier of the Service to retrieve.

        Returns:
            Service or None: The Service object if found, otherwise None.
        """

        return await self.db.get(Service, service_id)


    async def get_all_appointments(self, current_user: User):
        """
        Retrieve all appointments for the current user.
        Args:
            current_user (User): The user whose appointments are to be fetched.
        Returns:
            List[Appointment]: A list of Appointment objects associated with the current user.
        """

        result = await self.db.execute(
            select(Appointment).where(Appointment.customer_id == current_user.id)
        )
        return result.scalars().all()


    async def get_appointment(self, appointment_id: int, current_user: User) -> Appointment:
        """
        Retrieve an appointment by its ID for the current user.

        Returns:
            Appointment: The appointment object if found and belongs to the current user.
            list: An empty list if the appointment is not found or does not belong to the user.
        """

        result = await self.db.execute(
            select(Appointment).filter_by(
                id=appointment_id, customer_id=current_user.id
            )
        )
        appointment = result.scalar_one_or_none()

        if not appointment:
            return []  # appointment not found

        return appointment


    async def get_technician_appointment(self, current_user: User) -> Appointment:
        """
        Retrieve all appointments assigned to the currently authenticated technician.

        Args:
            current_user (User): The currently authenticated user, expected to be a technician.
        Returns:
            List[Appointment]: A list of Appointment objects assigned to the technician.
        """

        stmt = select(Appointment).where(Appointment.technician_id == current_user.id)
        result = await self.db.execute(stmt)
        return result.scalars().all()


    async def create_appointment(self, data: ScheduleAppointment, current_user: User) -> Appointment:
        """
        Asynchronously creates a new appointment for the current user.

        Returns:
            Appointment: The newly created appointment instance.
        Raises:
            HTTPException: If the specified service is not found for the user (404 error).
        """

        service_id = data.service_id
        service = await self._get_service(service_id)

        if not service:
            raise HTTPException(status_code=404, detail="Service not found for you!")

        # update customer_id and end_time in request body
        request_data = data.model_dump()
        request_data["customer_id"] = current_user.appointments
        request_data["end_time"] = request_data["scheduled_date"] + timedelta(
            minutes=service.duration_minutes
        )

        new_appointment = Appointment(**request_data)

        self.db.add(new_appointment)
        await self.db.commit()
        await self.db.refresh(new_appointment)
        return new_appointment


    async def update_scheduled_appointment(self, appointment_id: int, data: UpdateScheduledAppointment, current_user: User):
        """
        Asynchronously updates an existing appointment with the provided data.

        Returns:
            Appointment: The updated appointment object if found and updated.
            list: An empty list if the appointment does not exist.
        """

        appointment = await self.get_appointment(appointment_id, current_user)

        if not appointment:
            return []

        if data.scheduled_date:
            service = await self._get_service(appointment.service_id)
            appointment.scheduled_date = data.scheduled_date
            appointment.end_time = data.scheduled_date + timedelta(
                minutes=service.duration_minutes
            )

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(appointment, field, value)

        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment


    async def update_notes_or_status(self, appointment_id: int, data: UpdateScheduledAppointment, current_user: User):
        """
        Updates the status or technician notes of a scheduled appointment.

        Args:
            appointment_id (int): The ID of the appointment to update.
            data (UpdateScheduledAppointment): An object containing the new status and/or notes.
            current_user (User): The user performing the update operation.

        Returns:
            Appointment: The updated appointment object.

        Raises:
            HTTPException: If the appointment does not exist or the user is not authorized to update it.
        """

        appointment = await self.get_appointment(appointment_id, current_user)

        # Update allowed fields only (status and technician notes)
        if not (data.status or data.notes):
            raise HTTPException(status_code=400, detail="You're only allowed to update notes or status!")

        if data.status:
            appointment.status = data.status

        if data.notes:
            appointment.notes = data.notes

        await self.db.commit()
        await self.db.refresh(appointment)
        return appointment


    async def delete_scheduled_appointment(self, appointment_id: int, current_user) -> None:
        """
        Asynchronously deletes an appointment by its ID if it was scheduled by the current user.

        Returns:
            list: An empty list if the appointment does not exist for the current user.
        """

        appointment = await self.get_appointment(appointment_id, current_user)

        if not appointment:
            return []

        await self.db.delete(appointment)
        await self.db.commit()
