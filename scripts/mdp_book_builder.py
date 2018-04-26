#!/usr/bin/env python

"""
Build and display orderbooks from a given pcap file
"""

import sys
import os.path
import gzip

import dpkt
import binascii

from mdp.secdef import SecDef
from mdp.orderbook import PacketProcessor
from mdp.orderbook import ConsolePrinter

from sbedecoder import MDPSchema
from sbedecoder import MDPMessageFactory
from sbedecoder import SBEParser


def process_file(args, pcap_filename, security_id_filter=None, print_data=False):
    mdp_schema = MDPSchema()
    # Read in the schema xml as a dictionary and construct the various schema objects
    try:
        from sbedecoder.generated import __messages__ as generated_messages
        mdp_schema.load(generated_messages)
    except:
        mdp_schema.parse(args.schema)

    msg_factory = MDPMessageFactory(mdp_schema)
    mdp_parser = SBEParser(msg_factory)

    secdef = SecDef()
    secdef.load(args.secdef)

    book_builder = PacketProcessor(mdp_parser, secdef, security_id_filter=security_id_filter)

    console_printer = ConsolePrinter()
    book_builder.orderbook_handler = console_printer

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
                    data = udp.data
                    try:
                        if print_data:
                            print('data: {}'.format(binascii.b2a_hex(data)))
                        book_builder.handle_packet(long(ts*1000000), data)
                    except Exception as e:
                        print('Error decoding e:{} message:{}'.format(e, binascii.b2a_hex(data)))


def process_command_line():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description='Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.',
        version='0.1')

    parser.add_argument('pcapfile',
        help='Name of the pcap file to process')

    parser.add_argument('-s', '--schema', default='templates_FixBinary.xml',
        help='Name of the SBE schema xml file')

    parser.add_argument('-d', '--secdef', default='secdef.dat.gz',
        help='Name of the security definition file')

    parser.add_argument('-i', '--ids', default='',
        help='Comma separated list of security ids to display books for')

    parser.add_argument("--print-data", action='store_true',
        help="Print the data as an ascii hex string (default: %(default)s)")

    args = parser.parse_args()

    # check number of arguments, verify values, etc.:
    if not os.path.isfile(args.schema):
        parser.error('sbe schema xml file "{}" not found'.format(args.schema))

    if not os.path.isfile(args.secdef):
        parser.error('Security definition file "{}" not found'.format(args.secdef))


    return args


def main(argv=None):
    args = process_command_line()
    security_id_filter = None
    if args.ids:
        security_id_filter = [int(x.strip().lstrip()) for x in args.ids.split(',')]
    process_file(args, args.pcapfile, security_id_filter, args.print_data)
    return 0  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
