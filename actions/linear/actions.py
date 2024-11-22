from sema4ai.actions import action, Response, Secret
import json
import requests
from models import Issue, IssueList, FilterOptions, Team, TeamList, Project, ProjectList
from support import (
    _get_api_key,
    _set_query_variables,
    query_search_issues,
    query_get_issues,
    _get_state_id,
    _get_team_id,
    _get_project_id,
)

API_URL = "https://api.linear.app/graphql"


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
        API_URL,
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
        input_vars["assigneeId"] = issue_details.assignee.id
    if issue_details.project:
        input_vars["projectId"] = _get_project_id(issue_details, projects)
    if issue_details.state:
        input_vars["stateId"] = _get_state_id(issue_details, team_id, teams)

    variables = {"input": input_vars}

    response = requests.post(
        API_URL,
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
        API_URL,
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


# @action
# def update_issue(
#     api_key: Secret,
#     issue_id: str,
#     title: str = None,
#     description: str = None,
#     state_id: str = None,
#     assignee_id: str = None,
#     priority: int = None,
# ) -> Response[Issue]:
#     """Update a Linear issue

#     Args:
#         issue_id: ID of the issue to update
#         title: New title for the issue
#         description: New description for the issue
#         state_id: ID of the new state
#         assignee_id: ID of the user to assign the issue to
#         priority: Priority level (0-4)
#         api_key: The API key to use to authenticate with the Linear API
#     Returns:
#         The updated issue details
#     """
#     mutation = """
#     mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
#         issueUpdate(id: $id, input: $input) {
#             success
#             issue {
#                 id
#                 title
#                 description
#                 state {
#                     name
#                 }
#                 assignee {
#                     name
#                 }
#                 priority
#                 project {
#                     name
#                 }
#             }
#         }
#     }
#     """

#     # Build input variables with only provided fields
#     input_vars = {}
#     if title is not None:
#         input_vars["title"] = title
#     if description is not None:
#         input_vars["description"] = description
#     if state_id is not None:
#         input_vars["stateId"] = state_id
#     if assignee_id is not None:
#         input_vars["assigneeId"] = assignee_id
#     if priority is not None:
#         input_vars["priority"] = priority

#     variables = {"id": issue_id, "input": input_vars}

#     response = requests.post(
#         API_URL,
#         json={"query": mutation, "variables": variables},
#         headers={
#             "Authorization": _get_api_key(api_key),
#             "Content-Type": "application/json",
#         },
#     )

#     response_json = response.json()
#     if "errors" in response_json:
#         raise Exception(f"Failed to update issue: {response_json['errors']}")

#     issue_data = response_json["data"]["issueUpdate"]["issue"]

#     issue = Issue(
#         id=issue_data["id"],
#         title=issue_data["title"],
#         description=issue_data.get("description"),
#         assignee=issue_data["assignee"]["name"] if issue_data.get("assignee") else None,
#         project=issue_data["project"]["name"] if issue_data.get("project") else None,
#         state=issue_data["state"]["name"] if issue_data.get("state") else None,
#     )

#     return Response(result=issue)


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
        API_URL,
        json={"query": query, "variables": variables},
        headers={
            "Authorization": _get_api_key(api_key),
            "Content-Type": "application/json",
        },
    )

    response_json = response.json()
    return Response(result=json.dumps(response_json))
    # return Response(result=response_json["data"]["team"]["states"]["nodes"])


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
        API_URL,
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
        API_URL,
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
