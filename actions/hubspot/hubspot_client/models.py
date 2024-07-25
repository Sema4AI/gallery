from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class Owner(BaseModel):
    id: Annotated[str, Field(description="User unique identifier")]
    email: Annotated[str, Field(description="Email address")]
    first_name: Annotated[str | None, Field(description="First name")] = None
    last_name: Annotated[str | None, Field(description="Last name")] = None


class CompanyInfo(BaseModel):
    name: Annotated[str, Field(description="Company name")]
    domain: Annotated[str, Field(description="Company domain")]
    city: Annotated[str | None, Field(description="Company city")] = None
    state: Annotated[str | None, Field(description="Company state")] = None
    industry: Annotated[str | None, Field(description="Company industry")] = None


class Company(CompanyInfo):
    """Company entity data."""

    id: Annotated[str, Field(description="Company ID")]


class UpdateCompany(CompanyInfo):
    name: Annotated[str | None, Field(description="Company name")] = None
    domain: Annotated[str | None, Field(description="Company domain")] = None


class ContactInfo(BaseModel):
    email: Annotated[str, Field(description="Contact e-mail address")]
    firstname: Annotated[str | None, Field(description="Contact first name")] = None
    lastname: Annotated[str | None, Field(description="Contact last name")] = None
    phone: Annotated[str | None, Field(description="Contact phone number")] = None


class UpdateContact(ContactInfo):
    email: Annotated[str | None, Field(description="Contact e-mail address")] = None


class Contact(ContactInfo):
    """Contact entity data."""

    id: Annotated[str, Field(description="Contact ID")]


class Deal(BaseModel):
    """Deal entity data."""

    id: Annotated[str, Field(description="Deal ID")]
    dealname: Annotated[str, Field(description="Deal name")]
    amount: Annotated[str, Field(description="Deal money amount")]
    closedate: Annotated[str, Field(description="Deal close date")]
    dealstage: Annotated[str, Field(description="Deal stage")]


class UpdateDeal(BaseModel):
    dealname: Annotated[str | None, Field(description="Deal name")] = None
    amount: Annotated[str | None, Field(description="Deal money amount")] = None
    closedate: Annotated[str | None, Field(description="Deal close date")] = None
    dealstage: Annotated[str | None, Field(description="Deal stage")] = None
    hubspot_owner_id: Annotated[str | None, Field(description="Owner ID")] = None


class PipelineStage(BaseModel):
    id: Annotated[str, Field(description="Pipeline stage ID")]
    label: Annotated[str, Field(description="Pipeline stage label")]
    archived: Annotated[bool, Field(description="Pipeline stage archived")]


class Pipeline(BaseModel):
    id: Annotated[str, Field(description="Pipeline ID")]
    label: Annotated[str, Field(description="Pipeline label")]
    archived: Annotated[bool, Field(description="Pipeline stage archived")]
    stages: Annotated[list[PipelineStage], Field(description="Pipeline stages")]


class CreateDeal(BaseModel):
    dealname: Annotated[str, Field(description="Deal name")]
    dealstage: Annotated[str, Field(description="Deal stage ID")]
    amount: Annotated[str | None, Field(description="Deal money amount")] = None
    closedate: Annotated[str | None, Field(description="Deal close date")] = None
    hubspot_owner_id: Annotated[str | None, Field(description="Owner ID")] = None


class Ticket(BaseModel):
    """Ticket entity data."""

    id: Annotated[str, Field(description="Ticket ID")]
    subject: Annotated[str, Field(description="Ticket name")]
    content: Annotated[str, Field(description="Ticket content")]
    createdate: Annotated[str, Field(description="Ticket create date")]
    hs_ticket_priority: Annotated[str, Field(description="Ticket priority")]
    hs_pipeline_stage: Annotated[str, Field(description="Ticket status")]


class CreateTicket(BaseModel):
    subject: Annotated[str, Field(description="Ticket name")]
    content: Annotated[str, Field(description="Ticket content")]
    hs_ticket_priority: Annotated[str, Field(description="Ticket priority")]
    hs_pipeline_stage: Annotated[str, Field(description="Ticket stage ID")]
    hubspot_owner_id: Annotated[str | None, Field(description="Owner ID")] = None


class UpdateTicket(BaseModel):
    subject: Annotated[str | None, Field(description="Ticket name")] = None
    content: Annotated[str | None, Field(description="Ticket content")] = None
    hs_ticket_priority: Annotated[str | None, Field(description="Priority")] = None
    hs_pipeline_stage: Annotated[str | None, Field(description="Stage ID")] = None
    hubspot_owner_id: Annotated[str | None, Field(description="Owner ID")] = None


class _ObjectResult(BaseModel):
    """Object entity data."""

    id: Annotated[str, Field(description="Object ID")]
    hs_createdate: Annotated[str, Field(description="Object create date")]

    @classmethod
    def get_properties(cls) -> list[str]:
        return list(cls.model_fields.keys())


class TaskInfo(BaseModel):
    hs_task_subject: Annotated[str | None, Field(description="Task title")] = None
    hs_task_body: Annotated[str | None, Field(description="Task notes")] = None
    hubspot_owner_id: Annotated[str | None, Field(description="Task owner ID")] = None
    hs_task_status: Annotated[str | None, Field(description="Task status")] = None
    hs_task_priority: Annotated[
        str | None,
        Field(description="Task priority; valid values are: LOW, MEDIUM, or HIGH"),
    ] = None
    hs_task_type: Annotated[
        str | None,
        Field(description="Task type; valid values are: EMAIL, CALL, or TODO"),
    ] = None


class CreateTask(TaskInfo):
    hs_timestamp: Annotated[str, Field(description="Task due date")]


class Task(_ObjectResult):
    """Task object entity data."""

    hs_timestamp: Annotated[str, Field(description="Task due date")]

    def __str__(self):
        props = {
            "Task": self.hs_task_subject,
            "Owner": self.hubspot_owner_id,
            "Status": self.hs_task_status,
        }
        return " | ".join(f"{prop}: {value}" for prop, value in props.items())


class Operator(str, Enum):
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    EQ = "EQ"
    NEQ = "NEQ"
    BETWEEN = "BETWEEN"
    IN = "IN"
    NOT_IN = "NOT_IN"
    HAS_PROPERTY = "HAS_PROPERTY"
    NOT_HAS_PROPERTY = "NOT_HAS_PROPERTY"
    CONTAINS_TOKEN = "CONTAINS_TOKEN"
    NOT_CONTAINS_TOKEN = "NOT_CONTAINS_TOKEN"


class Filter(BaseModel):
    propertyName: Annotated[str, Field(description="Property name to filter by")]
    operator: Annotated[
        Operator,
        Field(
            description=(
                "Filter operation value. Possible values include: "
                "- LT: Less than the specified value. "
                "- LTE: Less than or equal to the specified value. "
                "- GT: Greater than the specified value. "
                "- GTE: Greater than or equal to the specified value. "
                "- EQ: Equal to the specified value. "
                "- NEQ: Not equal to the specified value. "
                "- BETWEEN: Within the specified range. Use key-value pairs to set highValue and value. "
                "- IN: Included within the specified list. Searches by exact match. "
                "Include the list values in a values array. When searching a string property with this operator, "
                "values must be lowercase. "
                "- NOT_IN: Not included within the specified list. Include the list values in a values array. "
                "When searching a string property with this operator, values must be lowercase. "
                "- HAS_PROPERTY: Has a value for the specified property. "
                "- NOT_HAS_PROPERTY: Doesn't have a value for the specified property. "
                "- CONTAINS_TOKEN: Contains a token. Use wildcards (*) to complete a partial search. "
                "For example, use the value *@hubspot.com to retrieve contacts with a HubSpot email address. "
                "- NOT_CONTAINS_TOKEN: Doesn't contain a token."
            )
        ),
    ]
    value: Annotated[str | None, Field(description="Value to filter by")] = None
    highValue: Annotated[
        str | None,
        Field(
            description="The upper limit for filtering. "
            "This is used with the BETWEEN operator to specify the range's upper boundary"
        ),
    ] = None
    values: Annotated[
        list[str] | None,
        Field(
            description="A list of values for the IN operator, allowing the filter to match any of the provided values"
        ),
    ] = None


class Filters(BaseModel):
    filters: Annotated[list[Filter], Field(description="Filter")]


class FilterGroups(BaseModel):
    filterGroups: Annotated[
        list[Filters],
        Field(description="Grouped filters in order to simulate AND and OR operators"),
    ]


class SearchParams(BaseModel):
    query: Annotated[str | None, Field(description="Search query")] = None
    filter_groups: Annotated[
        list[FilterGroups] | None,
        Field(
            description="To include multiple filter criteria, you can group filters within filterGroups: "
            "- to apply AND logic, include a comma separated list of conditions within one set of filters. "
            "- to apply OR logic, include multiple filters within a filterGroup. You can include a maximum of three "
            "filterGroups with up to three filters in each group.",
        ),
    ] = None
    limit: Annotated[int | None, Field(description="Number of results to return")] = 10


class Intervals(str, Enum):
    YEAR = "year"
    MONTH = "month"
    QUARTER = "quarter"
    WEEK = "week"
    DAY = "day"
    HOUR = "hour"
    MINUTE = "minute"
    SECOND = "second"


class MarketingEmailQueryParams(BaseModel):
    startTimestamp: Annotated[
        str, Field(description="Start timestamp in ISO8601 format")
    ]
    endTimestamp: Annotated[str, Field(description="End timestamp in ISO8601 format")]


class Counters(BaseModel):
    sent: Annotated[int | None, Field(description="Sent emails")] = 0
    open: Annotated[int | None, Field(description="Opened value")] = 0
    delivered: Annotated[int | None, Field(description="Delivered emails")] = 0
    click: Annotated[int | None, Field(description="Clicked emails")] = 0
    spamreport: Annotated[int | None, Field(description="Spam reported emails")] = 0
    bounce: Annotated[int | None, Field(description="Bounced emails")] = 0
    unsubscribed: Annotated[int | None, Field(description="Unsubscribed emails")] = 0
    notsent: Annotated[int | None, Field(description="Not sent emails")] = 0


class DeviceBreakdown(BaseModel):
    open_device_type: Annotated[
        dict[str, int] | None, Field(description="Device type breakdown for opens")
    ] = None
    click_device_type: Annotated[
        dict[str, int] | None, Field(description="Device type breakdown for clicks")
    ] = None


class Aggregate(BaseModel):
    counters: Annotated[Counters | None, Field(description="Aggregate counters")] = None
    deviceBreakdown: Annotated[
        DeviceBreakdown | None, Field(description="Aggregate device breakdown")
    ] = None


class EmailStatisticsResponse(BaseModel):
    aggregate: Annotated[
        Aggregate | None, Field(description="Aggregate statistics")
    ] = None
