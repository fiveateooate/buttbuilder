"""
class for GCE group opertations
"""
from googleapiclient import errors

import buttlib


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
