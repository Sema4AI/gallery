import json

from models import FilterOptions, Issue, IssueList, ProjectFilterOptions, Project, ProjectList
from queries import (
    query_add_comment,
    query_create_issue,
    query_get_issues,
    query_search_issues,
    query_search_projects,
)
from sema4ai.actions import Response, Secret, action
from support import (
    _get_assignee_id,
    _get_label_ids,
    _get_project_id,
    _get_projects,
    _get_state_id,
    _get_team_id,
    _get_teams,
    _make_graphql_request,
    _set_default_variables,
    _set_query_variables,
)


@action
def search_issues(
    filter_options: FilterOptions,
    api_key: Secret,
) -> Response[IssueList]:
    """
    Search issues from Linear.

    The values for "ordering" can be "createdAt" or "updatedAt".
    Returns by default 50 issues matching the filter options.

    Args:
        api_key: The API key to use to authenticate with the Linear API.
        filter_options: The filter options to use to search for issues.

    Returns:
        List of issues.
    """
    filter_dict = _set_query_variables(filter_options)
    query_to_use = query_search_issues if filter_dict else query_get_issues
    query_variables = _set_default_variables(filter_options, filter_dict)

    tickets = IssueList()
    search_response = _make_graphql_request(query_to_use, query_variables, api_key)
    issues = (
        search_response["data"]["issues"]["nodes"]
        if "data" in search_response
        else search_response["issues"]["nodes"]
    )
    for issue in issues:
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
    projects_result = _get_projects(api_key)
    teams_result = _get_teams(api_key)
    team_id = _get_team_id(issue_details, teams_result)
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
        input_vars["projectId"] = _get_project_id(issue_details, projects_result)
    if issue_details.state:
        input_vars["stateId"] = _get_state_id(issue_details, team_id, teams_result)
    if issue_details.labels:
        label_ids = _get_label_ids(issue_details, api_key)
        if label_ids:
            input_vars["labelIds"] = label_ids
    variables = {"input": input_vars}

    issue_response = _make_graphql_request(query_create_issue, variables, api_key)
    return Response(result=json.dumps(issue_response))


@action
def add_comment(issue_id: str, body: str, api_key: Secret) -> Response[str]:
    """Add a comment to a Linear issue

    Args:
        issue_id: ID of the issue to comment on
        body: Text content of the comment
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        The created comment details
    """

    variables = {"input": {"issueId": issue_id, "body": body}}
    comment_response = _make_graphql_request(query_add_comment, variables, api_key)

    return Response(
        result=f"Comment added - link {comment_response['commentCreate']['comment']['url']}"
    )


@action
def search_projects(
    filter_options: ProjectFilterOptions,
    api_key: Secret,
) -> Response[ProjectList]:
    """
    Search projects from Linear.

    The values for "ordering" can be "createdAt" or "updatedAt".
    Returns by default 50 projects matching the filter options.

    Args:
        api_key: The API key to use to authenticate with the Linear API.
        filter_options: The filter options to use to search for projects.

    Returns:
        List of projects matching the filter criteria.
    """
    filter_dict = {}
    if filter_options.name:
        filter_dict["name"] = {"contains": filter_options.name}
    if filter_options.initiative:
        filter_dict["initiatives"] = {"some": {"name": {"contains": filter_options.initiative}}}

    query_variables = {
        "first": filter_options.limit if filter_options.limit else 50,
        "orderBy": filter_options.ordering.value if filter_options.ordering else "updatedAt",
    }
    if filter_dict:
        query_variables["filter"] = filter_dict

    search_response = _make_graphql_request(query_search_projects, query_variables, api_key)
    projects = search_response["projects"]["nodes"]
    
    # Filter by team name after fetching if team_name is specified
    if filter_options.team_name:
        projects = [
            p for p in projects 
            if any(
                team["name"].lower() == filter_options.team_name.lower() 
                for team in p.get("teams", {}).get("nodes", [])
            )
        ]
    
    project_list = ProjectList(nodes=[])
    for project_data in projects:
        project = Project.create(project_data)
        project_list.nodes.append(project)

    return Response(result=project_list)
