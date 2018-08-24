"""
zone operation functions
https://cloud.google.com/compute/docs/reference/latest/zoneOperations
"""

import time


def zone_wait(client, operation):
    """ input: connection, zone, and operation
        output: request result - json
        sleep/waits for zone operation to complete
    """
    print("Waiting for operation to complete ... ", end="")
    while True:
        result = client.connection.zoneOperations().get(project=client.project, zone=client.zone, operation=operation).execute()
        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result
        time.sleep(1)
