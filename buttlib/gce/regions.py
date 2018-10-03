"""
gcp region functions
https://cloud.google.com/compute/docs/reference/latest/regions
"""


def get_region(client):
    response = client.connection.regions().get(project=client.project, region=client.region).execute()
    return response


def list_regions(client):
    response = client.connection.regions().list(project=client.project).execute()
    return response
