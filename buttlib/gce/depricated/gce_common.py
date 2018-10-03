"""
functions used by multiple gce modules
"""
import time
from googleapiclient import errors

__SLEEP_TIME = 1

def wait_for_zone_operation(gce_conn, project, zone, operation):
    """ input: gce connection, project, zone, and operation
        output: request result - json
        sleep/waits for operation to complete
    """
    print("     Waiting for operation {} to finish ... ".format(operation), end="")
    while True:
        result = gce_conn.zoneOperations().get(
            project=project, zone=zone, operation=operation).execute()

        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(__SLEEP_TIME)

def wait_for_region_operation(gce_conn, project, region, operation):
    """ input: gce connection, project, region, and operation
        output: request result - json
        sleep/waits for operation to complete
    """
    print("    Waiting for operation {} to finish ... ".format(operation), end="")
    while True:
        result = gce_conn.regionOperations().get(
            project=project, region=region, operation=operation).execute()

        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(__SLEEP_TIME)

def wait_for_global_operation(gce_conn, project, operation):
    """ input: gce connection, project, and operation
        output: request result - json
        sleep/waits for operation to complete
    """
    print("    Waiting for operation {} to finish ... ".format(operation), end="")
    while True:
        result = gce_conn.globalOperations().get(
            project=project, operation=operation).execute()

        if result['status'] == 'DONE':
            print("done")
            if 'error' in result:
                raise Exception(result['error'])
            return result

    time.sleep(__SLEEP_TIME)

def get_region_info(gce_conn, project, region):
    """ input: gce connection, project, region
        output: json with region info
    """
    try:
        region_info = gce_conn.regions().get(project=project, region=region).execute()
        return region_info
    except errors.HttpError as exc:
        print(exc)
