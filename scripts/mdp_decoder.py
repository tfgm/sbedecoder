#!/usr/bin/env python

"""
Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.
"""

import sys
import os.path
from sbedecoder import MDPSchema
from sbedecoder import MDPMessageFactory
from sbedecoder import SBEParser
import mdp.prettyprinter
import mdp.secdef
import mdp.decode
import gzip
import dpkt
from datetime import datetime


def process_file(pcap_filename, mdp_parser, secdef, pretty_print, print_data, skip_fields):
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
                        timestamp = datetime.fromtimestamp(ts)
                        mdp.decode.decode_packet(mdp_parser, timestamp, udp.data, skip_fields, print_data, pretty_print, secdef)
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

    # Read in the schema xml as a dictionary and construct the various schema objects
    mdp_schema = MDPSchema()
    mdp_schema.parse(args.schema)
    msg_factory = MDPMessageFactory(mdp_schema)
    mdp_parser = SBEParser(msg_factory)

    secdef = None
    if args.secdef:
        secdef = mdp.secdef.SecDef()
        secdef.load(args.secdef)

    skip_fields = set(args.skip_fields.split(','))

    process_file(args.pcapfile, mdp_parser, secdef, args.pretty, args.print_data, skip_fields)
    return 0  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
