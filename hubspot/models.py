from typing import Annotated

from pydantic import BaseModel, Field


class CompanyResult(BaseModel):
    """Company entity data."""

    id: Annotated[str, Field(description="Company ID.")]
    name: Annotated[str, Field(description="Company name.")]


class CompaniesResult(BaseModel):
    """Companies search result object holding the queried information."""

    companies: Annotated[list[CompanyResult], Field(description="Searched companies.")]


class ContactResult(BaseModel):
    """Contact entity data."""

    id: Annotated[str, Field(description="Contact ID.")]
    email: Annotated[str, Field(description="Contact e-mail address.")]
    firstname: Annotated[str | None, Field("", description="Contact first name.")]
    lastname: Annotated[str | None, Field("", description="Contact last name.")]


class ContactsResult(BaseModel):
    """Contacts search result object holding the queried information."""

    contacts: Annotated[list[ContactResult], Field(description="Searched contacts.")]


class DealResult(BaseModel):
    """Deal entity data."""

    id: Annotated[str, Field(description="Deal ID.")]
    dealname: Annotated[str, Field(description="Deal name.")]
    amount: Annotated[str, Field(description="Deal money amount.")]
    closedate: Annotated[str, Field(description="Deal close date.")]
    dealstage: Annotated[str, Field(description="Deal stage.")]


class DealsResult(BaseModel):
    """Deals search result object holding the queried information."""

    deals: Annotated[list[DealResult], Field(description="Searched deals.")]
