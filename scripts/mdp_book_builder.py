#!/usr/bin/env python

"""
Build and display orderbooks from a given pcap file
"""

import sys
import os.path
import gzip

import dpkt

from orderbook import SecDef
from orderbook import PacketProcessor
from orderbook import ConsolePrinter

from sbedecoder import SBESchema
from sbedecoder import SBEMessageFactory
from sbedecoder import SBEParser


def process_file(args, pcap_filename, security_id_filter=None):
    mdp_schema = SBESchema()
    # Read in the schema xml as a dictionary and construct the various schema objects
    try:
        from sbedecoder.generated import __messages__ as generated_messages
        mdp_schema.load(generated_messages)
    except:
        mdp_schema.parse(args.schema)

    msg_factory = SBEMessageFactory(mdp_schema)
    mdp_parser = SBEParser(msg_factory)

    secdef = SecDef()
    secdef.load(args.secdef)

    book_builder = PacketProcessor(mdp_parser, secdef, security_id_filter=security_id_filter)

    console_printer = ConsolePrinter()
    book_builder.orderbook_handler = console_printer

    with gzip.open(pcap_filename) if pcap_filename.endswith('.gz') else open(pcap_filename) as pcap:
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
                        book_builder.handle_packet(long(ts*1000000), data)
                    except Exception:
                        continue


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
    process_file(args, args.pcapfile, security_id_filter)
    return 0  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
