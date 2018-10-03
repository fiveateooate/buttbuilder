"""
gce instance groups functions
https://cloud.google.com/compute/docs/reference/latest/instanceGroups
"""

from googleapiclient import errors
import buttlib


def list_groups(client):
    groups = []
    request = client.connection.instanceGroups().list(project=client.project, zone=client.zone)
    while request is not None:
        response = request.execute()
        for group in response["items"]:
            groups.append(group)
        request = client.connection.instanceGroups().list_next(previous_request=request, previous_response=response)
    return groups


def get_group(client, zone, name):
    group = {}
    try:
        group = client.connection.instanceGroups().get(project=client.project, zone=zone, instanceGroup=name).execute()
    except errors.HttpError as exc:
        if exc.resp.status == 404:
            group = {}
        else:
            group = None
            print(exc)
    return group


def create_group(client, zone, name, network_url):
    retval = get_group(client, zone, name)
    if not retval:
        try:
            group_config = {"name": name, "network": network_url, "region": client.region}
            operation = client.connection.instanceGroups().insert(project=client.project, zone=zone, body=group_config).execute()
            buttlib.gce.operations.zone_wait(client, zone, operation['name'])
            retval = get_group(client, zone, name)
        except errors.HttpError as exc:
            print(exc)
            retval = None
    return retval


def delete_group(client, name):
    retval = {"name": name}
    return retval
    # try:
    #     operation = client.connection.instanceGroups().delete(project=client.project, zone=client.zone, instanceGroup=name).execute()
    #     buttlib.gce.zone_operations.zone_wait(client, operation['name'])
    #     retval = get_group(client, name)
    # except errors.HttpError as exc:
    #     print(exc)
    # return retval


def add_instance(client, group: str, instance, zone: str):
    retval = {}
    try:
        body = {"instances": [{"instance": instance}]}
        operation = client.connection.instanceGroups().addInstances(zone=zone, instanceGroup=group, body=body).execute()
        result = buttlib.gce.zone_operations.zone_wait(client, operation['name'])
        return result
    except errors.HttpError as exc:
        retval = None
        print(exc)
    return retval
