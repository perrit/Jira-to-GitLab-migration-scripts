import json
import requests
import sys

# === configuration ===

jira_base = 'https://my-organization.atlassian.net/rest/api/2'
jira_projects = ['my-project-code-1', 'my-project-code-2']
jira_auth = ('my-jira-username', 'my-jira-password')

gitlab_base = 'https://my-gitlab.example.com/api/v4/projects/my-project-id'
private_token = 'my-gitlab-token'

# === end of configuration ===

for jira_project in jira_projects:
    # fetch issues from jira
    issues = []
    startAt = 0
    total = 1
    while total > startAt:
        url = '%s/search?jql=project=%s+order+by+id+asc&startAt=%s' % (jira_base, jira_project, startAt)
        response = requests.get(url, auth=jira_auth)
        if response.status_code != 200:
            sys.stderr.write('%s %s' % (url, response.text))
            sys.exit(1)
        response_data = json.loads(response.text)
        startAt += response_data['maxResults']
        total = response_data['total']
        issues.extend(response_data['issues'])

    # perform sanity check
    if len(issues) != total:
        sys.stderr.write('Expected %s but retrieved %s issues.\n' % (total, len(issues)))
        sys.exit(1)

    # add issues to gitlab
    for issue in issues:
        # retrieve necessary fields from jira issue
        summary = issue['fields']['summary']
        created = issue['fields']['created']
        reporter = issue['fields']['reporter']['name']
        assignee = issue['fields']['assignee']['name'] if issue['fields']['assignee'] is not None else 'None'
        description = issue['fields']['description']

        # compile issue for gitlab
        data = dict()
        data['private_token'] = private_token
        data['title'] = summary
        data['created_at'] = created
        data['description'] = 'Reporter: %s\n\nAssignee: %s\n\n%s' % (reporter, assignee, description)

        # create issue in gitlab
        url = '%s/issues' % gitlab_base
        response = requests.post(url, data=data)
        if response.status_code != 201:
            sys.stderr.write('%s %s' % (url, response.text))
            sys.exit(1)
        response_data = json.loads(response.text)
        gitlab_issue_id = response_data['iid']

        # update issue status in gitlab if necessary
        if issue['fields']['status']['statusCategory']['name'] == 'Done':
            url = '%s/issues/%s' % (gitlab_base, gitlab_issue_id)
            data = dict()
            data['private_token'] = private_token
            data['state_event'] = 'close'
            response = requests.put(url, data=data)
            if response.status_code != 200:
                sys.stderr.write('%s %s' % (url, response.text))
                sys.exit(1)

        # fetch comments from jira
        jira_issue_id = issue['id']
        url = '%s/issue/%s?fields=comment' % (jira_base, jira_issue_id)
        response = requests.get(url, auth=jira_auth)
        if response.status_code != 200:
            sys.stderr.write('%s %s' % (url, response.text))
            sys.exit(1)
        response_data = json.loads(response.text)
        comments = response_data['fields']['comment']['comments']

        # add comments to gitlab
        for comment in comments:
            # retrieve necessary fields from jira comment
            author = comment['author']['name']
            created = comment['created']
            body = comment['body']

            # compile comment for gitlab
            data = dict()
            data['private_token'] = private_token
            data['issue_id'] = gitlab_issue_id
            data['created_at'] = created
            data['body'] = 'Author: %s\n\n%s' % (author, body)

            # create comment in gitlab
            url = '%s/issues/%s/notes' % (gitlab_base, gitlab_issue_id)
            response = requests.post(url, data=data)
            if response.status_code != 201:
                sys.stderr.write('%s %s' % (url, response.text))
                sys.exit(1)
