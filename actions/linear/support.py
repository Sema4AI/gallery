import json
import os
from pathlib import Path
from typing import List

import sema4ai_http
from dotenv import load_dotenv
from models import FilterOptions, Issue, Project, ProjectList, Team, TeamList
from queries import (
    query_create_label,
    query_get_labels,
    query_get_projects,
    query_get_states,
    query_get_teams,
    query_get_users,
)
from sema4ai.actions import Secret

GRAPHQL_API_URL = "https://api.linear.app/graphql"

load_dotenv(Path(__file__).absolute().parent / "devdata" / ".env")


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
    return filter_dict


def _set_default_variables(filter_options: FilterOptions, filter_dict: dict):
    query_variables = {
        "first": filter_options.limit if filter_options.limit else 50,
        "orderBy": (
            filter_options.ordering.value if filter_options.ordering else "updatedAt"
        ),
    }
    if filter_dict:
        query_variables["filter"] = filter_dict
    return query_variables


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
    response_data = _make_graphql_request(query_get_labels, {}, api_key, paginated=True)
    existing_labels = response_data["issueLabels"]["nodes"]
    label_ids = []
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
            create_response = _make_graphql_request(
                query_create_label,
                variables,
                api_key,
            )
            new_label_id = create_response["issueLabelCreate"]["issueLabel"]["id"]
            label_ids.append(new_label_id)
            if "errors" in create_response:
                raise Exception(f"Failed to create label: {create_response['errors']}")

    return label_ids


def _make_graphql_request(
    query: str, variables: dict, api_key: Secret, paginated: bool = False
) -> dict:
    """Make a GraphQL request to the Linear API, handling pagination if needed

    Args:
        query: The GraphQL query or mutation to execute
        variables: Variables to pass to the query
        api_key: The API key to use for authentication
        paginated: Whether to handle pagination for this request
    Returns:
        The JSON response data from the API, with all pages combined if paginated
    """
    all_data = []
    has_next_page = True
    after = None
    while has_next_page:
        current_variables = {**variables}
        if paginated:
            current_variables["after"] = after
        response = sema4ai_http.post(
            GRAPHQL_API_URL,
            json={"query": query, "variables": current_variables},
            headers={
                "Authorization": _get_api_key(api_key),
                "Content-Type": "application/json",
            },
        )
        response_json = response.json()
        if "errors" in response_json:
            raise Exception(f"GraphQL request failed: {response_json['errors']}")
        if not paginated:
            return response_json["data"]
        # Handle pagination
        # Assume the first key in data is the one we want to paginate
        data_key = next(iter(response_json["data"]))
        data = response_json["data"][data_key]
        all_data.extend(data["nodes"])

        has_next_page = data["pageInfo"]["hasNextPage"]
        after = data["pageInfo"]["endCursor"]
    return {next(iter(response_json["data"])): {"nodes": all_data}}


def _get_assignee_id(issue_details: Issue, api_key: Secret) -> str:
    """Get user ID from assignee name

    Args:
        issue_details: Issue details
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        User ID if found, None otherwise
    """

    user_response = _make_graphql_request(query_get_users, {}, api_key, paginated=True)
    all_users = user_response["users"]["nodes"]

    # Try to match by exact name first
    user = next(
        (
            user
            for user in all_users
            if user["name"].lower() == issue_details.assignee.name.lower()
            or user.get("displayName", "").lower()
            == issue_details.assignee.name.lower()
            or issue_details.assignee.name.lower() in user["name"].lower()
        ),
        None,
    )

    return user["id"] if user else None


def _get_workflow_states(team_id: str, api_key: Secret) -> str:
    """Get all workflow states for a team

    Args:
        team_id: ID of the team
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of workflow states with their IDs and names
    """
    variables = {"teamId": team_id}
    states_response = _make_graphql_request(query_get_states, variables, api_key)
    return json.dumps(states_response)


def _get_teams(api_key: Secret) -> TeamList:
    """Get all teams from Linear

    Args:
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of teams with their IDs and names
    """
    teams_response = _make_graphql_request(query_get_teams, {}, api_key)
    teams = [Team.model_validate(team) for team in teams_response["teams"]["nodes"]]
    return teams


def _get_projects(api_key: Secret) -> ProjectList:
    """Get all projects from Linear

    Args:
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of projects with their IDs, names, and team info
    """

    projects_response = _make_graphql_request(query_get_projects, {}, api_key)
    projects = [
        Project.model_validate(project)
        for project in projects_response["projects"]["nodes"]
    ]
    return projects
