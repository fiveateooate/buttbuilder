"""
region operation functions
https://cloud.google.com/compute/docs/reference/latest/regionOperations
"""
import time


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
