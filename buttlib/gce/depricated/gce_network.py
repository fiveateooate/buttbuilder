"""
colletion of functions for gce networking
"""
#from googleapiclient import discovery
#import pprint
import time

from googleapiclient import errors

import buttlib


def create_network(gce_conn, name, iprange, project):
    retval = None
    try:
        network_config = {"name": name, "IPv4Range": iprange}
        operation = gce_conn.networks().insert(
            project=project, body=network_config).execute()
        network = buttlib.gce.gce_common.wait_for_global_operation(gce_conn, project, operation['name'])
        retval = network['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            retval = get_network_url(gce_conn, name, project)
        else:
            print(exc)
    return retval


def delete_network(gce_conn, name, project):
    try:
        print("deleting network")
        operation = gce_conn.networks().delete(
            project=project, network=name).execute()
        buttlib.gce.gce_common.wait_for_global_operation(gce_conn, project, operation['name'])
    except errors.HttpError as exc:
        print(exc)


def get_network_url(gce_conn, network_name, project):
    try:
        response = gce_conn.networks().get(project=project, network=network_name).execute()
        return response["selfLink"]
    except errors.HttpError as exc:
        print(exc)


def list_networks(gce_conn, project):
    response = gce_conn.networks().list(project=project).execute()
    return response["selfLink"]


def create_firewall_rules(gce_conn, network, name, proto, ports, source_range,
                          project):
    try:
        allowed = [{
            'IPProtocol': proto,
            'ports': ports
        }] if isinstance(ports, list) else [{
            'IPProtocol': proto,
            'ports': [ports]
        }]
        firewall_body = {
            'name': name,
            'allowed': allowed,
            'sourceRanges': source_range,
            'network': network
        }
        operation = gce_conn.firewalls().insert(
            project=project, body=firewall_body).execute()
        result = buttlib.gce.gce_common.wait_for_global_operation(gce_conn, project,
                                                      operation['name'])
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            result = gce_conn.firewalls().get(
                project=project, firewall=name).execute()
            return result['selfLink']
        else:
            print(exc)


def create_tcp_health_check(gce_conn, project, name, port):
    try:
        health_check_body = {
            "name": name,
            "type": "TCP",
            "tcpHealthCheck": {
                "port": port
            }
        }
        result = gce_conn.healthChecks().insert(
            project=project, body=health_check_body).execute()
        if result['status'] == "PENDING":
            time.sleep(5)
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            result = gce_conn.healthChecks().get(
                project=project, healthCheck=name).execute()
            return result['selfLink']
        else:
            print(exc)


def create_http_health_check(gce_conn, project, name, port):
    try:
        health_check_body = {"name": name, "port": port}
        result = gce_conn.httpHealthChecks().insert(
            project=project, body=health_check_body).execute()
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            result = gce_conn.httpHealthChecks().get(
                project=project, httpHealthCheck=name).execute()
            return result['selfLink']
        else:
            print(exc)


def create_internal_backend_service(gce_conn, project, region, name,
                                    instance_groups, port):
    try:
        health_check = create_tcp_health_check(gce_conn, project,
                                               "hc-%s" % name, port)
        backends = [{"group": v['url']} for k, v in instance_groups.items()]
        backend_service_body = {
            "name": name,
            "healthChecks": [health_check],
            "backends": backends,
            "loadBalancingScheme": "INTERNAL"
        }
        operation = gce_conn.regionBackendServices().insert(
            project=project, region=region,
            body=backend_service_body).execute()
        result = buttlib.gce.gce_common.wait_for_region_operation(
            gce_conn, project, region, operation['name'])
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            result = gce_conn.regionBackendServices().get(
                project=project, region=region, backendService=name).execute()
            return result['selfLink']
        else:
            print(exc)


def create_target_pool(gce_conn, name, project, region, port):
    try:
        health_check = create_http_health_check(gce_conn, project,
                                                "hc-%s" % name, port)
        pool_resource = {
            'name': name,
            'region': region,
            "healthChecks": [health_check]
        }
        operation = gce_conn.targetPools().insert(
            project=project, region=region, body=pool_resource).execute()
        result = buttlib.gce.gce_common.wait_for_region_operation(
            gce_conn, project, region, operation['name'])
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            result = gce_conn.targetPools().get(
                project=project, region=region, targetPool=name).execute()
            return result['selfLink']
        else:
            print(exc)


def create_forwarding_rule(gce_conn,
                           project,
                           region,
                           name,
                           backend_url,
                           proto,
                           portrange,
                           network=None,
                           internal=False,
                           ip=None):
    try:
        # goofy stuff for internal vs external load balancers
        forwarding_rule = {'name': name, 'region': region, 'IPProtocol': proto}
        if internal:
            forwarding_rule['loadBalancingScheme'] = "INTERNAL"
            forwarding_rule['backendService'] = backend_url
            forwarding_rule['ports'] = [portrange]
            forwarding_rule['network'] = network
        else:
            forwarding_rule['target'] = backend_url
            forwarding_rule['portRange'] = portrange

        if ip:
            forwarding_rule['IPAddress'] = ip
        operation = gce_conn.forwardingRules().insert(
            project=project, region=region, body=forwarding_rule).execute()
        result = buttlib.gce.gce_common.wait_for_region_operation(
            gce_conn, project, region, operation['name'])
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            result = gce_conn.forwardingRules().get(
                project=project, region=region, forwardingRule=name).execute()
            return result['selfLink']
        else:
            print(exc)


def add_to_target_pool(gce_conn, instances, target_pool, project, region):
    try:
        body = {
            "instances": instances
        } if isinstance(instances, list) else {
            "instances": [instances]
        }
        operation = gce_conn.targetPools().addInstance(
            project=project, region=region, targetPool=target_pool,
            body=body).execute()
        result = buttlib.gce.gce_common.wait_for_region_operation(
            gce_conn, project, region, operation['name'])
        return result['targetLink']
    except errors.HttpError as exc:
        if exc.resp.status == 409:
            print("targetpool 409'd something")
            print(exc)
        else:
            print(exc)
