from typing import Annotated

from pydantic import BaseModel, Field


class CompanyResult(BaseModel):
    """Company entity data."""

    id: Annotated[str, Field(description="Company ID")]
    name: Annotated[str, Field(description="Company name")]


class CompaniesResult(BaseModel):
    """Companies search result object holding the queried information."""

    companies: Annotated[list[CompanyResult], Field(description="Searched companies")]


class ContactResult(BaseModel):
    """Contact entity data."""

    id: Annotated[str, Field(description="Contact ID")]
    email: Annotated[str, Field(description="Contact e-mail address")]
    firstname: Annotated[str | None, Field("", description="Contact first name")]
    lastname: Annotated[str | None, Field("", description="Contact last name")]


class ContactsResult(BaseModel):
    """Contacts search result object holding the queried information."""

    contacts: Annotated[list[ContactResult], Field(description="Searched contacts")]


class DealResult(BaseModel):
    """Deal entity data."""

    id: Annotated[str, Field(description="Deal ID")]
    dealname: Annotated[str, Field(description="Deal name")]
    amount: Annotated[str, Field(description="Deal money amount")]
    closedate: Annotated[str, Field(description="Deal close date")]
    dealstage: Annotated[str, Field(description="Deal stage")]


class DealsResult(BaseModel):
    """Deals search result object holding the queried information."""

    deals: Annotated[list[DealResult], Field(description="Searched deals")]


class TicketResult(BaseModel):
    """Ticket entity data."""

    id: Annotated[str, Field(description="Ticket ID")]
    subject: Annotated[str, Field(description="Ticket name")]
    content: Annotated[str, Field(description="Ticket content")]
    createdate: Annotated[str, Field(description="Ticket create date")]
    hs_ticket_priority: Annotated[str, Field(description="Ticket priority")]
    hs_pipeline_stage: Annotated[str, Field(description="Ticket status")]


class TicketsResult(BaseModel):
    """Tickets search result object holding the queried information."""

    tickets: Annotated[list[TicketResult], Field(description="Searched tickets")]


class ObjectResult(BaseModel):
    """Object entity data."""

    id: Annotated[str, Field(description="Object ID")]
    hs_createdate: Annotated[str, Field(description="Object create date")]

    @classmethod
    def get_properties(cls) -> list[str]:
        return list(cls.model_fields.keys())


class TaskResult(ObjectResult):
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


class TasksResult(BaseModel):
    """Tasks search result object holding the queried information."""

    tasks: Annotated[list[TaskResult], Field(description="Searched tasks")]
