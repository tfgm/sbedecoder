#!/usr/bin/env python

"""
Parse a base64 replay file containing CME MDP3 market data based on a SBE xml schema file.
"""

import sys
import os.path
from sbedecoder import MDPSchema
from sbedecoder import MDPMessageFactory
from sbedecoder import SBEParser
import mdp.prettyprinter
import mdp.secdef
import mdp.decode
import base64
import gzip
import re
from datetime import datetime

def process_file(base64data_filename, mdp_parser, secdef, pretty_print, print_data, skip_fields):
    re_binascii_replay = re.compile(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}.\d{6})\s-\s((?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?)$')
    with gzip.open(base64data_filename, 'rb') if base64data_filename.endswith('.gz') else open(base64data_filename, 'rb') as packets:
        line_number = 0
        for packet_bytes in packets:
            packet = packet_bytes.decode("utf-8")
            line_number += 1
            m = re_binascii_replay.match(packet)
            if m:
                packet_data_ts = m.group(1)
                packet_dt = datetime.strptime(packet_data_ts, '%Y-%m-%d %H:%M:%S.%f')
                packet_data_binascii = m.group(2)
                packet_data = base64.b64decode(packet_data_binascii)
                if print_data:
                    print('data: {}'.format(packet_data_binascii))
                mdp.decode.decode_packet(mdp_parser, packet_dt, packet_data, skip_fields, print_data, pretty_print, secdef, line_number)


def process_command_line():
    from argparse import ArgumentParser
    from argparse import RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description='Parse a text file containing base64 encoded CME MDP3 market\n'
                    'data based on a SBE xml schema file.  File format is:\n'
                    '\n'
                    '  YYYY-MM-DD HH:MM:SS.ffffff - data\n'
                    '\n'
                    'where "data" is the base64 encoded dta\n',
        formatter_class=RawDescriptionHelpFormatter
    )

    parser.add_argument('base64data',
        help='Name of the base64 encoded file to process')

    parser.add_argument('-s', '--schema', default='templates_FixBinary.xml',
        help='Name of the SBE schema xml file')

    default_skip_fields = 'message_size,block_length,template_id,schema_id,version'

    parser.add_argument('-f', '--skip-fields', default=default_skip_fields,
        help='Don\'t print these message fields (default={})'.format(default_skip_fields))

    parser.add_argument('--print-data', action='store_true',
        help='Print the data as an ascii hex string (default: %(default)s)')

    parser.add_argument('--pretty', action='store_true',
        help='Print the message with a pretty format')

    parser.add_argument('--secdef',
        help='Name of the security definition file for augmenting logs with symbols')

    args = parser.parse_args()

    # check number of arguments, verify values, etc.:
    if not os.path.isfile(args.schema):
        parser.error('sbe schema xml file \'{}\' not found'.format(args.schema))

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

    process_file(args.base64data, mdp_parser, secdef, args.pretty, args.print_data, skip_fields)
    return 0  # success


if __name__ == '__main__':
    status = main()
    sys.exit(status)
