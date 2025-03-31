import json

from models import FilterOptions, Issue, IssueList, ProjectFilterOptions, Project, ProjectList, ProjectCreate, Initiative, InitiativeList, Team, TeamList, WorkflowStates
from queries import (
    query_add_comment,
    query_create_issue,
    query_get_issues,
    query_search_issues,
    query_search_projects,
    query_create_project,
    query_get_initiatives,
    query_get_teams_simple,
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


@action
def create_project(
    api_key: Secret,
    project_details: ProjectCreate,
) -> Response[str]:
    """Create a new Linear project

    Args:
        project_details: The details of the project to create
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        The created project details
    """
    teams_result = _get_teams(api_key)
    team_id = _get_team_id(Issue(team=project_details.team), teams_result)
    
    if not team_id:
        raise Exception(f"Could not find team: {project_details.team.name}")

    input_vars = {
        "name": project_details.name,
        "teamIds": [team_id],
    }

    # Add optional fields if provided
    if project_details.description:
        input_vars["description"] = project_details.description
    if project_details.content:
        input_vars["content"] = project_details.content
    if project_details.startDate:
        input_vars["startDate"] = project_details.startDate.isoformat()
    if project_details.targetDate:
        input_vars["targetDate"] = project_details.targetDate.isoformat()

    variables = {"input": input_vars}

    project_response = _make_graphql_request(query_create_project, variables, api_key)
    return Response(result=json.dumps(project_response))


@action
def get_initiatives(
    api_key: Secret,
) -> Response[InitiativeList]:
    """Get all initiatives from Linear

    Args:
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of initiatives with their IDs and names
    """
    initiatives_response = _make_graphql_request(query_get_initiatives, {}, api_key)
    initiatives = [
        Initiative.create(initiative)
        for initiative in initiatives_response["initiatives"]["nodes"]
    ]
    return Response(result=InitiativeList(nodes=initiatives))


@action
def get_teams(
    api_key: Secret,
) -> Response[TeamList]:
    """Get all teams from Linear with basic information (id and name)

    Args:
        api_key: The API key to use to authenticate with the Linear API
    Returns:
        List of teams with their IDs and names
    """
    teams_response = _make_graphql_request(query_get_teams_simple, {}, api_key)
    teams = [
        Team(
            id=team["id"],
            name=team["name"],
            key="",  # Required by model but not needed for simple view
            states=WorkflowStates(nodes=[])  # Required by model but not needed for simple view
        )
        for team in teams_response["teams"]["nodes"]
    ]
    return Response(result=TeamList(nodes=teams))
