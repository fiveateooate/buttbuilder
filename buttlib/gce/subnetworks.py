"""
gce subnetwork functions
https://cloud.google.com/compute/docs/reference/latest/subnetworks
"""

from googleapiclient import errors
import buttlib


def list(client):
    subnetworks = []
    request = client.connection.subnetworks().list(project=client.project, region=client.region)
    while request is not None:
        response = request.execute()
        for subnetwork in response["items"]:
            subnetworks.append(subnetwork)
        request = client.connection.subnetworks().list_next(previous_request=request, previous_response=response)
    return subnetworks


def get(client, subnetworkname):
    subnetwork = {}
    try:
        subnetwork = client.connection.subnetworks().get(project=client.project, region=client.region, subnetwork=subnetworkname).execute()
    except errors.HttpError as exc:
        if exc.resp.status == 404:
            subnetwork = {}
        else:
            subnetwork = None
            print(exc)
    return subnetwork


def create(client, subnetworkname, iprange, network_url):
    retval = get(client, subnetworkname)
    if not retval:
        try:
            subnetwork_config = {"name": subnetworkname, "ipCidrRange": iprange, "network": network_url}
            operation = client.connection.subnetworks().insert(project=client.project, region=client.region, body=subnetwork_config).execute()
            buttlib.gce.region_operations.wait(client, operation['name'])
            retval = get(client, subnetworkname)
        except errors.HttpError as exc:
            retval = None
            print(exc)
    return retval


def delete(client, subnetworkname):
    retval = {"name": subnetworkname}
    try:
        operation = client.connection.subnetworks().delete(project=client.project, region=client.region, subnetwork=subnetworkname).execute()
        buttlib.gce.region_operations.wait(client, operation['name'])
        retval = get(client, subnetworkname)
    except errors.HttpError as exc:
        print(exc)
    return retval
