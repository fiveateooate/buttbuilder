"""
gce instance groups functions
https://cloud.google.com/compute/docs/reference/latest/instanceGroups
"""

from googleapiclient import errors
import buttlib


def list(client):
    groups = []
    request = client.connection.instanceGroups().list(project=client.project, zone=client.zone)
    while request is not None:
        response = request.execute()
        for group in response["items"]:
            groups.append(group)
        request = client.connection.instanceGroups().list_next(previous_request=request, previous_response=response)
    return groups


def get(client, name):
    group = {}
    try:
        group = client.connection.instanceGroups().get(project=client.project, zone=client.zone, instanceGroup=name).execute()
    except errors.HttpError as exc:
        if exc.resp.status == 404:
            group = {}
        else:
            group = None
            print(exc)
    return group


def create(client, name, network_url):
    retval = get(client, name)
    if not retval:
        try:
            group_config = {"name": name, "network": network_url, "region": client.region}
            operation = client.connection.instanceGroups().insert(project=client.project, zone=client.zone, body=group_config).execute()
            result = buttlib.gce.zone_operations.wait(client, operation['name'])
            retval = get(client, name)
        except errors.HttpError as exc:
            print(exc)
            retval = None
    return retval


def delete(client, name):
    retval = {"name": name}
    try:
        operation = client.connection.instanceGroups().delete(project=client.project, zone=client.zone, instanceGroup=name).execute()
        buttlib.gce.zone_operations.wait(client, operation['name'])
        retval = get(client, name)
    except errors.HttpError as exc:
        print(exc)
    return retval


def add_instances(client, group, instance):
    retval = {}
    try:
        body = {"instances": [{"instance": instance}]}
        operation = client.connection.instanceGroups().addInstances(project=project, zone=zone, instanceGroup=group, body=body).execute()
        result = buttlib.gce.zone_operations.wait(client, operation['name'])
        return result
    except errors.HttpError as exc:
        retval = None
        print(exc)
    return retval
