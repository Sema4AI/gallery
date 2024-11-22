from sema4ai.actions import Secret
from dotenv import load_dotenv
from pathlib import Path
import os
from models import FilterOptions, Issue, TeamList, ProjectList

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")

nodes = """
    {
        id
        title
        description
        state {
            id
            name
        }
        assignee {
            id
            name
        }
        creator {
            id
            name
        }
        project {
            id
            name
        }
        priority
        team {
            id
            name
        }
        url
        createdAt
        updatedAt
    }
"""

query_search_issues = f"""
    query SearchIssues($filter: IssueFilter) {{
        issues(filter: $filter) {{
            nodes {nodes}
        }}
    }}
"""

query_get_issues = f"""
    query GetIssues($orderBy: PaginationOrderBy) {{
        issues(orderBy: $orderBy) {{
            nodes {nodes}
        }}
    }}
"""


def _set_query_variables(filter_options: FilterOptions) -> dict:
    filter_dict = {}
    if filter_options.assignee_name:
        filter_dict["assignee"] = {
            "name": {"contains": filter_options.assignee_name}
        }  # {"eq": filter_options.assignee_name}}
    if filter_options.title:
        filter_dict["title"] = {"contains": filter_options.title}
    if filter_options.project_name:
        filter_dict["project"] = {"name": {"contains": filter_options.project_name}}
    if filter_options.creator_name:
        filter_dict["creator"] = {"name": {"contains": filter_options.creator_name}}
    if filter_options.description:
        filter_dict["description"] = {"contains": filter_options.description}
    if filter_options.state:
        filter_dict["state"] = {"name": {"contains": filter_options.state}}
    if filter_options.team_name:
        filter_dict["team"] = {"name": {"contains": filter_options.team_name}}
    variables = {"filter": filter_dict} if filter_dict else {}
    return variables


def _get_api_key(api_key: Secret) -> str:
    if api_key.value:
        return api_key.value
    else:
        return os.getenv("LINEAR_API_KEY")


def _get_team_id(issue_details: Issue, teams_data: TeamList) -> str:
    team_id = issue_details.team.id
    if not team_id:
        team = next(
            (
                team
                for team in teams_data
                if issue_details.team.name.lower() in team.name.lower()
            ),
            None,
        )
        team_id = team.id
    return team_id


def _get_state_id(issue_details: Issue, team_id: str, teams_data: TeamList) -> str:
    state_id = issue_details.state.id
    if not state_id:
        # Find the team first
        team = next((team for team in teams_data if team.id == team_id), None)
        if team:
            # Find the state in that team
            state = next(
                (
                    state
                    for state in team.states.nodes
                    if state.name.lower() == issue_details.state.name.lower()
                ),
                None,
            )
            return state.id if state else None
    return state_id


def _get_project_id(issue_details: Issue, projects_data: ProjectList) -> str:
    project_id = issue_details.project.id
    if not project_id:
        project = next(
            (
                project
                for project in projects_data
                if project.name == issue_details.project.name
            ),
            None,
        )
        return project.id if project else None
    return project_id
