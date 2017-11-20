#!/usr/bin/env python3

import argparse
import importlib
import os


def build(args, cluster_config_info, builder):
    try:
        builder.build()
        # builder.update_kube_config()
    except buttlib.common.MissingEnvVarsError as exception:
        print(exception)
    except buttlib.common.IncompleteEnvironmentSetup as exception:
        print(exception)
    except buttlib.exceptions.LibVirtConnectionError as exception:
        print(exception)
    except buttlib.common.DoNotDestroyCluster as exception:
        print(exception)


def node(args, cluster_config_info, builder):
    if args.action == 'add':
        for i in range(0, args.count):
            print("adding a node")
            builder.add_node()
    if args.action == 'remove' and args.name is not None:
        builder.remove_node(args.name)


def firewall(args, cluster_config_info, builder):
    if args.action == 'add':
        ports = args.ports.split(",")
        builder.createFireWallRules(args.proto, ports, args.sourcerange)
    elif args.action == 'delete':
        print("delete rule %s" % args.name)
    else:
        print("unknow action")


def loadbalancer(args, cluster_config_info, builder):
    if args.action == "add":
        builder.create_load_balancer()
    elif args.action == "remove":
        builder.deleteLoadBalancer()


def network(args, cluster_config_info, builder):
    if args.action == "list":
        builder.listNetworks()
    elif args.action == "add":
        builder.create_network()
    elif args.action == "remove":
        builder.deleteNetwork()


def verify(args, cluster_config_info, builder):
    print("Verifying butt state")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='make clusters in butts')
    # required args to identify cluster
    parser.add_argument('--cenv', help="environment name", required=True)
    parser.add_argument('--cid', help="cluster identifier", required=True)
    # output modifiers
    parser.add_argument('--dryrun', '-d', help="dry run", action='store_true')
    parser.add_argument('--verbose', '-v', help="verbose", action='store_true')
    # base config
    parser.add_argument('--config', '-c', help="path to cluster_config/yaml file if github is not working", default=None)
    parser.add_argument('--buttdir', help="directory to store cluster data")
    # operations
    subparsers = parser.add_subparsers(title="buttbuilder operations", help='do things with butts')
    parser_build = subparsers.add_parser('build', help='Build a butt')
    # parser_build.add_argument('--createcluster', help='build cluster',action="store_true")
    parser_build.set_defaults(func=build)

    parser_node = subparsers.add_parser('node', help='Manage butt nodes')
    parser_node.add_argument('--action', help='node actions', choices=["add", "remove"])
    parser_node.add_argument('--name', help='node name to remove')
    parser_node.add_argument("--count", help="nodes to add", default=1, type=int)
    parser_node.set_defaults(func=node)

    parser_firewall = subparsers.add_parser('firewall', help='Manage butt firewall')
    parser_firewall.add_argument('--action', help='firewall rule actions', choices=["add", "remove"], required=True)
    parser_firewall.add_argument('--proto', help='tcp,udp', required=True)
    parser_firewall.add_argument('--ports', help='comma separated list of ports', required=True)
    parser_firewall.add_argument('--sourcerange', help='rource range', default="0.0.0.0/0")
    parser_firewall.set_defaults(func=firewall)

    parser_loadbalancer = subparsers.add_parser('loadbalancer', help='Manage butt loadbalancers')
    parser_loadbalancer.add_argument('--action', help='loadbalancer actions', choices=["add", "remove"])
    parser_loadbalancer.set_defaults(func=loadbalancer)

    parser_network = subparsers.add_parser('network', help='Manage butt networks')
    parser_network.add_argument('--action', help='network actions', choices=["add", "remove", "list"])
    parser_network.set_defaults(func=network)
    parser_verify = subparsers.add_parser('verify', help='Verify butt state')
    parser_verify.set_defaults(func=verify)
    args = parser.parse_args()

    if not hasattr(args, 'func'):
        parser.print_help()
        parser.exit()

    os.environ['provider'] = ""
    import buttlib.helpers
    cluster_config_info = buttlib.helpers.ClusterConfigHandler(args.cenv, args.cid, args.config)

    os.environ['provider'] = cluster_config_info.env_info['provider']
    import buttlib

    builder_class = getattr(importlib.import_module("buttlib.{provider}.{provider}_builder".format(provider=cluster_config_info.env_info['provider'])), "Builder")

    builder = builder_class(cluster_config_info.env_info, args)
    args.func(args, cluster_config_info, builder)
