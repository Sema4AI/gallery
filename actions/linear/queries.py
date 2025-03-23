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
query SearchIssues($filter: IssueFilter, $orderBy: PaginationOrderBy, $first: Int = 50) {{
    issues(filter: $filter, orderBy: $orderBy, first: $first) {{
        nodes {nodes}
    }}
}}
"""

query_get_issues = f"""
query GetIssues($orderBy: PaginationOrderBy, $first: Int = 50) {{
    issues(orderBy: $orderBy, first: $first) {{
        nodes {nodes}
    }}
}}
"""


query_create_label = """
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

query_get_labels = """
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

query_get_users = """
query Users($after: String) {
    users(first: 250, after: $after) {
        nodes {
            id
            name
            email
            displayName
        }
        pageInfo {
            hasNextPage
            endCursor
        }
    }
}
"""

query_create_issue = """
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
query_add_comment = """
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
            url
        }
    }
}
"""
query_get_projects = """
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

query_get_teams = """
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

query_get_states = """
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

query_search_projects = """
query SearchProjects($filter: ProjectFilter, $orderBy: PaginationOrderBy, $first: Int = 50) {
    projects(filter: $filter, orderBy: $orderBy, first: $first) {
        nodes {
            id
            name
            description
            startDate
            targetDate
            teams {
                nodes {
                    id
                    name
                }
            }
            initiatives {
                nodes {
                    id
                    name
                }
            }
            url
            createdAt
            updatedAt
        }
    }
}
"""
