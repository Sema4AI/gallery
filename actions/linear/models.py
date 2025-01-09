from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Annotated, List, Optional


class OrderType(str, Enum):
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"


class FilterOptions(BaseModel):
    assignee_name: Optional[str] = None
    creator_name: Optional[str] = None
    project_name: Optional[str] = None
    team_name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    state: Optional[str] = None
    label: Optional[str] = None
    limit: Optional[int] = None
    ordering: Optional[OrderType] = Field(default=OrderType.UPDATED_AT)


class NameAndId(BaseModel):
    name: Optional[str] = None
    id: Optional[str] = None


class Issue(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    assignee: Optional[NameAndId] = None
    creator: Optional[NameAndId] = None
    project: Optional[NameAndId] = None
    description: Optional[str] = None
    team: Optional[NameAndId] = None
    state: Optional[NameAndId] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    labels: Optional[List[NameAndId]] = None

    @classmethod
    def create(cls, data: dict) -> "Issue":
        """Create an Issue instance from Linear API data

        Args:
            data: Dictionary containing issue data from Linear API
        Returns:
            New Issue instance with populated fields
        """
        return cls(
            id=data.get("id"),
            title=data.get("title"),
            description=data.get("description"),
            assignee=(
                NameAndId(
                    name=data.get("assignee", {}).get("name"),
                    id=data.get("assignee", {}).get("id"),
                )
                if data.get("assignee")
                else None
            ),
            creator=(
                NameAndId(
                    name=data.get("creator", {}).get("name"),
                    id=data.get("creator", {}).get("id"),
                )
                if data.get("creator")
                else None
            ),
            project=(
                NameAndId(
                    name=data.get("project", {}).get("name"),
                    id=data.get("project", {}).get("id"),
                )
                if data.get("project")
                else None
            ),
            team=(
                NameAndId(
                    name=data.get("team", {}).get("name"),
                    id=data.get("team", {}).get("id"),
                )
                if data.get("team")
                else None
            ),
            state=(
                NameAndId(
                    name=data.get("state", {}).get("name"),
                    id=data.get("state", {}).get("id"),
                )
                if data.get("state")
                else None
            ),
            labels=(
                [
                    NameAndId(name=label.get("name", ""), id=label.get("id", ""))
                    for label in data.get("labels", {}).get("nodes", [])
                ]
                if data.get("labels")
                else None
            ),
            url=data.get("url"),
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )


class IssueList(BaseModel):
    issues: Annotated[List[Issue], Field(default_factory=list)] = []

    def add_ticket(self, ticket: Issue):
        """Add a ticket to the list

        Args:
            ticket: The ticket to add
        """
        self.issues.append(ticket)


class WorkflowState(BaseModel):
    id: str
    name: str
    type: str
    color: str


class WorkflowStates(BaseModel):
    nodes: List[WorkflowState]


class Team(BaseModel):
    id: str
    name: str
    key: str
    description: Optional[str] = None
    states: WorkflowStates


class TeamList(BaseModel):
    nodes: List[Team]


class Project(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    startDate: Optional[datetime] = None
    targetDate: Optional[datetime] = None


class ProjectList(BaseModel):
    nodes: List[Project]


class LabelList(BaseModel):
    labels: Annotated[List[str], Field(default_factory=list)] = []

    def add_label(self, label: str):
        """Add a label to the list
        Args:
            label: The label to add
        """
        self.labels.append(label)
