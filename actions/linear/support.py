from sema4ai.actions import Secret
from dotenv import load_dotenv
import os
from pathlib import Path
import requests
from models import FilterOptions, Issue, TeamList, ProjectList
from typing import List

GRAPHQL_API_URL = "https://api.linear.app/graphql"

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
        labels {
            nodes {
                id
                name
                color
            }
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
    if filter_options.label:
        filter_dict["labels"] = {"some": {"name": {"contains": filter_options.label}}}
    variables = {"filter": filter_dict} if filter_dict else {}
    return variables


def _get_api_key(api_key: Secret) -> str:
    if api_key.value:
        return api_key.value
    else:
        return os.getenv("LINEAR_API_KEY")


def _get_team_id(issue_details: Issue, teams_data: TeamList) -> str:
    team = next(
        (
            team
            for team in teams_data
            if issue_details.team.name.lower() in team.name.lower()
        ),
        None,
    )
    return team.id if team else None


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


def _get_label_ids(issue_details: Issue, api_key: Secret) -> List[str]:
    """Get label IDs from label names, creating new labels if they don't exist

    Args:
        issue_details: Issue details containing labels
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of label IDs
    """
    # First get existing labels
    query = """
    query Labels($after: String) {
        issueLabels(first: 250, after: $after) {
            nodes {
                id
                name
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """
    existing_labels = []
    has_next_page = True
    after = None
    # Fetch all labels using pagination
    while has_next_page:
        response = requests.post(
            GRAPHQL_API_URL,
            json={"query": query, "variables": {"after": after}},
            headers={
                "Authorization": _get_api_key(api_key),
                "Content-Type": "application/json",
            },
        )
        response_json = response.json()
        if "errors" in response_json:
            raise Exception(f"Failed to fetch labels: {response_json['errors']}")
        data = response_json["data"]["issueLabels"]
        existing_labels.extend(data["nodes"])

        has_next_page = data["pageInfo"]["hasNextPage"]
        after = data["pageInfo"]["endCursor"]

    label_ids = []

    # Mutation to create new label
    create_label_mutation = """
    mutation CreateLabel($input: IssueLabelCreateInput!) {
        issueLabelCreate(input: $input) {
            success
            issueLabel {
                id
                name
            }
        }
    }
    """

    for issue_label in issue_details.labels:
        # Try to find existing label
        label = next(
            (
                label
                for label in existing_labels
                if label["name"].lower() == issue_label.name.lower()
            ),
            None,
        )

        if label:
            label_ids.append(label["id"])
        else:
            # Create new label if it doesn't exist
            variables = {
                "input": {
                    "name": issue_label.name,
                    "color": "#000000",  # Default color, you might want to make this configurable
                }
            }

            create_response = requests.post(
                GRAPHQL_API_URL,
                json={"query": create_label_mutation, "variables": variables},
                headers={
                    "Authorization": _get_api_key(api_key),
                    "Content-Type": "application/json",
                },
            )

            create_response_json = create_response.json()
            if "errors" in create_response_json:
                raise Exception(
                    f"Failed to create label: {create_response_json['errors']}"
                )

            new_label_id = create_response_json["data"]["issueLabelCreate"][
                "issueLabel"
            ]["id"]
            label_ids.append(new_label_id)

    return label_ids
