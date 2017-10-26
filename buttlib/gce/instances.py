"""
gce instance functions
https://cloud.google.com/compute/docs/reference/latest/instances
"""

import buttlib
from googleapiclient import errors


def list(client):
    retval = []
    region_info = buttlib.gce.regions.get(client)
    for zone in region_info['zones']:
        zone_name = (zone.split("/")[-1]).strip()
        request = client.connection.instances().list(project=client.project, zone=zone_name)
        while request is not None:
            response = request.execute()
            if 'items' in response:
                for instance in response['items']:
                    retval.append(instance)
            request = client.connection.instances().list_next(previous_request=request, previous_response=response)
    return retval


def get(client, instance_name):
    instance = {}
    try:
        instance = client.connection.instances().get(project=client.project, zone=client.zone, instance=instance_name).execute()
    except errors.HttpError as exc:
        if exc.resp.status == 404:
            instance = {}
        else:
            instance = None
            print(exc)
    return instance


def create(client, body):
    instance = {}
    try:
        operation = client.connection.instances().insert(project=client.project, zone=client.zone, body=body).execute()
        buttlib.gce.zone_operations.wait(client, zone, operation['name'])
        retval = get(client, zone, body['name'])
    except errors.HttpError as exc:
        retval = None
        print(exc)
    return retval


def delete(client, instance):
    pass


def start(client, instance):
    pass
