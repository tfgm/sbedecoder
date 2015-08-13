#!/usr/bin/env python

"""
Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.
"""

import sys
import os.path
from optparse import OptionParser
from optparse import TitledHelpFormatter
from struct import unpack_from
from datetime import datetime
from sbedecoder import SBESchema
from sbedecoder import SBEMessageFactory
from sbedecoder import SBEParser
import gzip
import dpkt


def parse_mdp3_packet(mdp_parser, ts, data, skip_fields):
    timestamp = datetime.fromtimestamp(ts)
    # parse the packet header: http://www.cmegroup.com/confluence/display/EPICSANDBOX/MDP+3.0+-+Binary+Packet+Header
    sequence_number = unpack_from("<i", data, offset=0)[0]
    sending_time = unpack_from("<Q", data, offset=4)[0]
    print(':packet - timestamp: {} sequence_number: {} sending_time: {} '.format(
        timestamp, sequence_number, sending_time))
    for mdp_message in mdp_parser.parse(data, offset=12):
        message_fields = ''
        for field in mdp_message.fields:
            if field.name not in skip_fields:
                message_fields += ' ' + str(field)
        print('::{} - {}'.format(mdp_message, message_fields))
        for iterator in mdp_message.iterators:
            print(':::{} - num_groups: {}'.format(iterator.name, iterator.num_groups))
            for index, group in enumerate(iterator):
                group_fields = ''
                for group_field in group.fields:
                    group_fields += str(group_field) + ' '
                print('::::{}'.format(group_fields))


def process_file(options, pcap_filename):
    # Read in the schema xml as a dictionary and construct the various schema objects
    mdp_schema = SBESchema()
    mdp_schema.parse(options.schema_filename)
    msg_factory = SBEMessageFactory(mdp_schema)
    mdp_parser = SBEParser(msg_factory)

    skip_fields = set(options.skip_fields.split(','))

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
                    try:
                        parse_mdp3_packet(mdp_parser, ts, udp.data, skip_fields)
                    except Exception:
                        print('could not parse packet number {}'.format(packet_number))


def process_command_line(argv):
    """
    Return a 2-tuple: (options object, args list).
    `argv` is a list of arguments, or `None` for ``sys.argv[1:]``.
    """
    if argv is None:
        argv = sys.argv[1:]

    # initialize the parser object:
    parser = OptionParser(
        formatter=TitledHelpFormatter(width=120),
        add_help_option=None,
        version='%prog  0.1',
        usage='usage: %prog [options] pcapfile'
    )

    parser.description = 'Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.'

    parser.add_option("-s", "--schema", dest="schema_filename", default='templates_FixBinary.xml',
                      help="Don't print messages to standard out")

    default_skip_fields = 'message_size,block_length,template_id,schema_id,version'

    parser.add_option("-f", "--skip-fields", dest="skip_fields", default=default_skip_fields,
                      help="Don't print these message fields (default={})".format(default_skip_fields))

    parser.add_option(  # customized description; put --help last
        '-h', '--help', action='help', help='Show this help message and exit.')

    options, args = parser.parse_args(argv)

    # check number of arguments, verify values, etc.:
    if not os.path.isfile(options.schema_filename):
        parser.error("schema file '{}' not found".format(options.schema_filename))

    if len(args) != 1:
        parser.error("no file specified")

    if not os.path.isfile(argv[0]):
        parser.error("pcap file '{}' not found".format(argv[0]))

    return options, args


def main(argv=None):
    options, args = process_command_line(argv)
    process_file(options, args[0])
    return 0  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
