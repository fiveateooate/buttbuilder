"""
gce regionalInstanceGroups functions
https://cloud.google.com/compute/docs/reference/latest/regionInstanceGroups
was not what I thought, seems you have to use instance templates ...
"""


def list(client):
    groups = []
    request = client.connection.regionalInstanceGroups().list(project=client.project)
    while request is not None:
        response = request.execute()
        for group in response["items"]:
            groups.append(group)
        request = client.connection.instanceGroups().list_next(previous_request=request, previous_response=response)
    return groups


def get(client, name):
    group = {}
    try:
        group = client.connection.regionalInstanceGroups().get(project=client.project, instanceGroup=name).execute()
    except errors.HttpError as exc:
        if exc.resp.status == 404:
            group = {}
        else:
            group = None
            print(exc)
    return group
