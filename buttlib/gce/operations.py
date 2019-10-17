"""gce operations: like waiting and stuff"""

import time


def zone_wait(client, zone, operation):
    """ input: connection, zone, and operation
        output: request result - json
        sleep/waits for zone operation to complete
    """
    print("Waiting for operation to complete ... ", end="")
    while True:
        result = client.connection.zoneOperations().get(project=client.project, zone=zone, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        time.sleep(1)


def region_wait(client, operation):
    """ input: gce connection and operation
        output: request result - json
        sleep/waits for region operation to complete
    """
    print("Waiting for operation to complete ... ", end="")
    while True:
        result = client.connection.regionOperations().get(project=client.project, region=client.region, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        time.sleep(1)


def global_wait(client, operation):
    """ input: gce client and operation
        output: request result - json
        sleep/waits for global operation to complete
    """
    print("Waiting for operation to complete ... ", end="")
    while True:
        result = client.connection.globalOperations().get(project=client.project, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        time.sleep(1)
