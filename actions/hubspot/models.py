from typing import Annotated

from pydantic import BaseModel, Field


class Company(BaseModel):
    """Company entity data."""

    id: Annotated[str, Field(description="Company ID")]
    name: Annotated[str, Field(description="Company name")]


class Contact(BaseModel):
    """Contact entity data."""

    id: Annotated[str, Field(description="Contact ID")]
    email: Annotated[str, Field(description="Contact e-mail address")]
    firstname: Annotated[str | None, Field("", description="Contact first name")]
    lastname: Annotated[str | None, Field("", description="Contact last name")]


class Deal(BaseModel):
    """Deal entity data."""

    id: Annotated[str, Field(description="Deal ID")]
    dealname: Annotated[str, Field(description="Deal name")]
    amount: Annotated[str, Field(description="Deal money amount")]
    closedate: Annotated[str, Field(description="Deal close date")]
    dealstage: Annotated[str, Field(description="Deal stage")]


class Ticket(BaseModel):
    """Ticket entity data."""

    id: Annotated[str, Field(description="Ticket ID")]
    subject: Annotated[str, Field(description="Ticket name")]
    content: Annotated[str, Field(description="Ticket content")]
    createdate: Annotated[str, Field(description="Ticket create date")]
    hs_ticket_priority: Annotated[str, Field(description="Ticket priority")]
    hs_pipeline_stage: Annotated[str, Field(description="Ticket status")]


class _ObjectResult(BaseModel):
    """Object entity data."""

    id: Annotated[str, Field(description="Object ID")]
    hs_createdate: Annotated[str, Field(description="Object create date")]

    @classmethod
    def get_properties(cls) -> list[str]:
        return list(cls.model_fields.keys())


class Task(_ObjectResult):
    """Task object entity data."""

    hs_task_subject: Annotated[str, Field(description="Task title")]
    hs_task_body: Annotated[str, Field(description="Task notes")]
    hubspot_owner_id: Annotated[str, Field(description="Task owner ID")]
    hs_timestamp: Annotated[str, Field(description="Task due date")]
    hs_task_status: Annotated[str, Field(description="Task status")]
    hs_task_priority: Annotated[str, Field(description="Task priority")]
    hs_task_type: Annotated[str, Field(description="Task type")]

    def __str__(self):
        props = {
            "Task": self.hs_task_subject,
            "Owner": self.hubspot_owner_id,
            "Status": self.hs_task_status,
        }
        return " | ".join(f"{prop}: {value}" for prop, value in props.items())
