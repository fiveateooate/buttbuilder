"""
colletion of functions for gce networking
https://cloud.google.com/compute/docs/reference/latest/networks
"""

from googleapiclient import errors
import buttlib


def list_networks(client):
    networks = []
    request = client.connection.networks().list(project=client.project)
    while request is not None:
        response = request.execute()
        for network in response["items"]:
            networks.append(network)
        request = client.connection.networks().list_next(previous_request=request, previous_response=response)
    return networks


def get_network(client, network_name):
    network = {}
    try:
        network = client.connection.networks().get(project=client.project, network=network_name).execute()
    except errors.HttpError as exc:
        if exc.resp.status == 404:
            network = {}
        else:
            network = None
            print(exc)
    return network


def create_network(client, name):
    retval = get_network(client, name)
    if not retval:
        try:
            network_config = {"name": name, "autoCreateSubnetworks": False}
            operation = client.connection.networks().insert(project=client.project, body=network_config).execute()
            buttlib.gce.global_operations.wait(client, operation['name'])
            retval = get_network(client, name)
        except errors.HttpError as exc:
            retval = None
            print(exc)
    return retval


def delete_network(client, name):
    retval = {"name": name}
    try:
        operation = client.connection.networks().delete(project=client.project, network=name).execute()
        buttlib.gce.global_operations.wait(client, operation['name'])
        retval = get_network(client, name)
    except errors.HttpError as exc:
        print(exc)
    return retval
