#!/usr/bin/env python

"""
Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.
"""

import sys
import os.path
from struct import unpack_from
from datetime import datetime
import binascii
from sbedecoder import SBESchema
from sbedecoder import SBEMessageFactory
from sbedecoder import SBEParser
import mdp.prettyprinter
import mdp.secdef
import gzip
import dpkt


def handle_repeating_groups(group_container, msg_version, indent, skip_fields, secdef):
    for group in group_container.groups:
        if group.since_version > msg_version:
            continue
        print(':::{} - num_groups: {}'.format(group.name, group.num_groups))
        for group_field in group.repeating_groups:
            group_fields = ''
            for group_field in group_field.fields:
                if group_field.since_version > msg_version:
                    continue
                if secdef and group_field.id == '48':
                    security_id = group_field.value
                    symbol_info = secdef.lookup_security_id(security_id)
                    if symbol_info:
                        symbol = symbol_info[0]
                        group_fields += 'security_id: {} [{}]'.format(security_id, symbol) + ' '
                        continue
                group_fields += str(group_field) + ' '
            print('::::{}'.format(group_fields))
        handle_repeating_groups(group, msg_version, indent + ':', skip_fields=skip_fields, secdef=secdef)


def parse_mdp3_packet(mdp_parser, ts, data, skip_fields, print_data, pretty, secdef):
    if print_data:
        print('data: {}'.format(binascii.b2a_hex(data)))

    timestamp = datetime.fromtimestamp(ts)
    # parse the packet header: http://www.cmegroup.com/confluence/display/EPICSANDBOX/MDP+3.0+-+Binary+Packet+Header
    sequence_number = unpack_from("<i", data, offset=0)[0]
    sending_time = unpack_from("<Q", data, offset=4)[0]

    print(':packet - timestamp: {} sequence_number: {} sending_time: {} '.format(
        timestamp, sequence_number, sending_time))

    if pretty:
        # Two-passes on the parse so we can count the messages and print e.g. "Message 3 of 5"
        #
        # Cannot store messages from the iteration, as field objects get reused and overwritten
        # on each round.
        n = len(list(mdp_parser.parse(data, offset=12)))  # pass 1 to count the msgs in iterable

        for i, mdp_message in enumerate(mdp_parser.parse(data, offset=12)):  # pass 2 to actually print
            mdp.prettyprinter.pretty_print(mdp_message, i, n, secdef)
    else:
        for mdp_message in mdp_parser.parse(data, offset=12):
            message_fields = ''
            for field in mdp_message.fields:
                if field.since_version > mdp_message.version.value:  # field is later version than msg
                    continue
                if field.name not in skip_fields:
                    message_fields += ' ' + str(field)
            print('::{} - {}'.format(mdp_message, message_fields))
            handle_repeating_groups(mdp_message, mdp_message.version.value, indent='::::', skip_fields=skip_fields, secdef=secdef)


def process_file(args, pcap_filename, print_data):
    # Read in the schema xml as a dictionary and construct the various schema objects
    mdp_schema = SBESchema()
    mdp_schema.parse(args.schema)
    msg_factory = SBEMessageFactory(mdp_schema)
    mdp_parser = SBEParser(msg_factory)

    secdef = None
    if args.secdef:
        secdef = mdp.secdef.SecDef()
        secdef.load(args.secdef)

    skip_fields = set(args.skip_fields.split(','))

    with gzip.open(pcap_filename, 'rb') if pcap_filename.endswith('.gz') else open(pcap_filename, 'rb') as pcap:
        pcap_reader = dpkt.pcap.Reader(pcap)
        packet_number = 0
        for ts, packet in pcap_reader:
            packet_number += 1
            ethernet = dpkt.ethernet.Ethernet(packet)
            if ethernet.type == dpkt.ethernet.ETH_TYPE_IP:
                ip = ethernet.data
                if ip.p == dpkt.ip.IP_PROTO_UDP:
                    udp = ip.data
                    try:
                        parse_mdp3_packet(mdp_parser, ts, udp.data, skip_fields, print_data, args.pretty, secdef)
                    except Exception as e:
                        print('Error parsing packet #{} - {}'.format(packet_number, e))


def process_command_line():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.",
        version="0.1")

    parser.add_argument("pcapfile",
        help="Name of the pcap file to process")

    parser.add_argument("-s", "--schema", default='templates_FixBinary.xml',
        help="Name of the SBE schema xml file")

    default_skip_fields = 'message_size,block_length,template_id,schema_id,version'

    parser.add_argument("-f", "--skip-fields", default=default_skip_fields,
        help="Don't print these message fields (default={})".format(default_skip_fields))

    parser.add_argument("--print-data", action='store_true',
        help="Print the data as an ascii hex string (default: %(default)s)")

    parser.add_argument("--pretty", action='store_true',
        help="Print the message with a pretty format")

    parser.add_argument('--secdef',
        help='Name of the security definition file for augmenting logs with symbols')

    args = parser.parse_args()

    # check number of arguments, verify values, etc.:
    if not os.path.isfile(args.schema):
        parser.error("sbe schema xml file '{}' not found".format(args.schema))

    return args


def main(argv=None):
    args = process_command_line()
    process_file(args, args.pcapfile, args.print_data)
    return 0  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
