from sema4ai.actions import action, Response, Secret
import json
import requests
from models import Issue, IssueList, FilterOptions, Team, TeamList, Project, ProjectList
from support import (
    GRAPHQL_API_URL,
    _get_api_key,
    _set_query_variables,
    query_search_issues,
    query_get_issues,
    _get_label_ids,
    _get_state_id,
    _get_team_id,
    _get_project_id,
)


@action
def search_issues(
    filter_options: FilterOptions,
    api_key: Secret,
) -> Response[IssueList]:
    """
    Search issues from Linear.

    Args:
        api_key: The API key to use to authenticate with the Linear API.
        filter_options: The filter options to use to search for issues.

    Returns:
        List of issues.
    """
    variables = _set_query_variables(filter_options)
    query_data = {"query": query_search_issues if variables else query_get_issues}
    variables["orderBy"] = "updatedAt"
    query_data["variables"] = json.dumps(variables)
    response = requests.post(
        GRAPHQL_API_URL,
        json=query_data,  # Add variables to the request
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )
    tickets = IssueList()
    response_json = response.json()
    for issue in response_json["data"]["issues"]["nodes"]:
        ticket = Issue.create(issue)
        tickets.add_ticket(ticket)

    return Response(result=tickets)


@action
def create_issue(
    api_key: Secret,
    issue_details: Issue,
) -> Response[str]:
    """Create a new Linear issue

    Args:
        issue_details: The details of the issue to create
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        The created issue details
    """
    mutation = """
    mutation CreateIssue($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue {
                id
                identifier
                title
                description
                team {
                    id
                    name
                }
                project {
                    id
                    name
                }
                assignee {
                    name
                }
                creator {
                    name
                }
                state {
                    id
                    name
                }
                labels {
                    nodes {
                        id
                        name
                    }
                }
                url
            }
        }
    }
    """
    projects_result = get_projects(api_key)
    projects = projects_result.result
    teams_result = get_teams(api_key)
    teams = teams_result.result
    team_id = _get_team_id(issue_details, teams)
    input_vars = {
        "teamId": team_id,
        "title": issue_details.title,
    }

    # Add optional fields if provided
    if issue_details.description:
        input_vars["description"] = issue_details.description
    if issue_details.assignee:
        input_vars["assigneeId"] = _get_assignee_id(issue_details, api_key)
    if issue_details.project:
        input_vars["projectId"] = _get_project_id(issue_details, projects)
    if issue_details.state:
        input_vars["stateId"] = _get_state_id(issue_details, team_id, teams)
    if issue_details.labels:
        label_ids = _get_label_ids(issue_details, api_key)
        if label_ids:
            input_vars["labelIds"] = label_ids
    variables = {"input": input_vars}

    response = requests.post(
        GRAPHQL_API_URL,
        json={"query": mutation, "variables": variables},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()

    if "errors" in response_json:
        raise Exception(f"Failed to create issue: {response_json['errors']}")

    return Response(result=json.dumps(response_json))


@action
def add_comment(issue_id: str, body: str, api_key: Secret) -> str:
    """Add a comment to a Linear issue

    Args:
        issue_id: ID of the issue to comment on
        body: Text content of the comment
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        The created comment details
    """
    mutation = """
    mutation CreateComment($input: CommentCreateInput!) {
        commentCreate(input: $input) {
            success
            comment {
                id
                body
                createdAt
                user {
                    name
                }
            }
        }
    }
    """

    variables = {"input": {"issueId": issue_id, "body": body}}

    response = requests.post(
        GRAPHQL_API_URL,
        json={"query": mutation, "variables": variables},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()
    if "errors" in response_json:
        raise Exception(f"Failed to create comment: {response_json['errors']}")

    return "Comment added"


@action
def get_workflow_states(team_id: str, api_key: Secret) -> Response[str]:
    """Get all workflow states for a team

    Args:
        team_id: ID of the team
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of workflow states with their IDs and names
    """
    query = """
    query WorkflowStates($teamId: String!) {
        team(id: $teamId) {
            states {
                nodes {
                    id
                    name
                    type
                    color
                }
            }
        }
    }
    """

    variables = {"teamId": team_id}

    response = requests.post(
        GRAPHQL_API_URL,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()
    return Response(result=json.dumps(response_json))


@action
def get_teams(api_key: Secret) -> Response[TeamList]:
    """Get all teams from Linear

    Args:
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of teams with their IDs and names
    """
    query = """
    query Teams {
        teams {
            nodes {
                id
                name
                key
                description
                states {
                    nodes {
                        id
                        name
                        type
                        color
                    }
                }
            }
        }
    }
    """

    response = requests.post(
        GRAPHQL_API_URL,
        json={"query": query},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()
    if "errors" in response_json:
        raise Exception(f"Failed to fetch teams: {response_json['errors']}")
    teams = [
        Team.model_validate(team) for team in response_json["data"]["teams"]["nodes"]
    ]
    return Response(result=teams)


@action
def get_projects(api_key: Secret) -> Response[ProjectList]:
    """Get all projects from Linear

    Args:
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of projects with their IDs, names, and team info
    """
    query = """
    query Projects {
        projects {
            nodes {
                id
                name
                description
                startDate
                targetDate
            }
        }
    }
    """

    response = requests.post(
        GRAPHQL_API_URL,
        json={"query": query},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()
    if "errors" in response_json:
        raise Exception(f"Failed to fetch projects: {response_json['errors']}")

    projects = [
        Project.model_validate(project)
        for project in response_json["data"]["projects"]["nodes"]
    ]
    return Response(result=projects)


def _get_assignee_id(issue_details: Issue, api_key: Secret) -> str:
    """Get user ID from assignee name

    Args:
        issue_details: Issue details
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        User ID if found, None otherwise
    """
    query = """
    query Users {
        users {
            nodes {
                id
                name
                email
                displayName
            }
        }
    }
    """

    response = requests.post(
        GRAPHQL_API_URL,
        json={"query": query},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()
    if "errors" in response_json:
        raise Exception(f"Failed to fetch users: {response_json['errors']}")

    users = response_json["data"]["users"]["nodes"]

    # Try to match by exact name first
    user = next(
        (
            user
            for user in users
            if user["name"].lower() == issue_details.assignee.name.lower()
            or user.get("displayName", "").lower()
            == issue_details.assignee.name.lower()
            or issue_details.assignee.name.lower() in user["name"].lower()
        ),
        None,
    )

    return user["id"] if user else None
