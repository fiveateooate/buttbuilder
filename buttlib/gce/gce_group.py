"""
class for GCE group opertations
"""
from googleapiclient import errors

import buttlib


def create_instance_group(gce_conn, project, zone, name, network):
    try:
        group_config = {"name": name, "network": network}
        operation = gce_conn.instanceGroups().insert(
            project=project, zone=zone, body=group_config).execute()
        result = buttlib.gce.gce_common.wait_for_zone_operation(gce_conn, project, zone, operation['name'])
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            retval = gce_conn.instanceGroups().get(
                project=project, zone=zone, instanceGroup=name).execute()
            return retval['selfLink']
        else:
            print(exc)


def add_instance_to_group(gce_conn, project, zone, group, instance):
    try:
        body = {"instances": [{"instance": instance}]}
        operation = gce_conn.instanceGroups().addInstances(
            project=project, zone=zone, instanceGroup=group,
            body=body).execute()
        result = buttlib.gce.gce_common.wait_for_zone_operation(gce_conn, project, zone, operation['name'])
        return result
    except errors.HttpError as exc:
        print(exc)
