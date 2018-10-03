"""
global operations functions
https://cloud.google.com/compute/docs/reference/latest/globalOperations
"""
import time


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
