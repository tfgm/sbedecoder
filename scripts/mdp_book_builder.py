#!/usr/bin/env python

"""
Build and display orderbooks from a given pcap file
"""

import sys
import os.path
from struct import unpack_from
from sbedecoder import SBESchema
from sbedecoder import SBEMessageFactory
from sbedecoder import SBEParser
import gzip
import dpkt


class OrderBookEntry(object):
    def __init__(self, index, price, size, num_orders):
        self.index = index
        self.price = price
        self.size = size
        self.num_orders = num_orders

    def __str__(self):
        return "{{{0:<6}}} {1:>6} {2:>34}".format(self.num_orders, self.size, self.price,)


class OrderBook(object):
    def __init__(self, security_id):
        self.security_id = security_id
        self.bids = []
        self.offers = []
        self.stream_sequence_number = -1
        self.instrument_sequence_number = -1
        self.valid = False
        self.sending_time = None

    def invalidate(self):
        self.valid = False
        self.sending_time = None
        self.stream_sequence_number = -1
        self.instrument_sequence_number = -1
        self.bids = []
        self.offers = []

    def update(self, md_entry_type, md_update_action, stream_sequence_number,
               sending_time, instr_sequence_number, index,
               price, size, num_orders):

        # We only care about outright changes for now
        if md_entry_type not in ['Bid', 'Offer']:
            return False

        if md_update_action not in ['Change', 'New', 'Delete']:
            return False

        is_bid = (md_entry_type == 'Bid')
        update_list = self.bids
        if not is_bid:
            update_list = self.offers

        self.stream_sequence_number = stream_sequence_number
        self.instrument_sequence_number = instr_sequence_number
        self.sending_time = sending_time

        if md_update_action == 'Change':
            self.modify(update_list, index, price, size, num_orders)
        elif md_update_action == 'New':
            self.insert(update_list, index, price, size, num_orders)
        elif md_update_action == 'Delete':
            self.insert(update_list, index, price, size, num_orders)

        return True

    @staticmethod
    def _find_book_entry(entries, index):
        for book_entry in entries:
            if book_entry.index == index:
                return book_entry
        return None

    def insert(self, entries, index, price, size, num_orders):
        existing_entry = self._find_book_entry(entries, index)
        if existing_entry is not None:
            existing_entry.price = price
            existing_entry.size = size
            existing_entry.num_orders = num_orders
            return

        # The entry wasn't found we should add it in
        new_entry = OrderBookEntry(index, price, size, num_orders)
        entries.append(new_entry)

    def modify(self, entries, index, price, size, num_orders):
        # We treat modifies and inserts the same for natural refresh
        self.insert(entries, index, price, size, num_orders)

    def delete_level(self, entries, index, price, size, num_orders):
        existing_entry = self._find_book_entry(entries, index)
        if existing_entry is not None:
            entries.remove(existing_entry)

    def __str__(self):
        result = "{0:>50}\n".format(self.sending_time,)
        result += "Security Id: {0:11} SSN: {1:20}\n".format(self.security_id, self.stream_sequence_number,)
        for offer in sorted(self.offers, key=lambda x: x.index, reverse=True):
            result += "{0:50}\n".format(str(offer),)
        result += "-" * 50
        result += "\n"
        for bid in sorted(self.bids, key=lambda x: x.index):
            result += "{0:50}\n".format(str(bid),)
        return result


class OrderBookBuilder(object):
    def __init__(self, mdp_parser, security_id_filter=None):
        self.mdp_parser = mdp_parser
        self.security_id_filter = security_id_filter

        self.stream_sequence_number = -1
        self.sending_time = None

        self.orderbook_handler = None

        # We only keep track of the base books, implieds aren't handled
        self.base_orderbooks = {}

    def _invalidate_books(self):
        for security_id, orderbook in self.base_orderbooks.items():
            orderbook.invalidate()

    def handle_packet(self, mdp_packet):
        sequence_number = unpack_from("<i", mdp_packet, offset=0)[0]
        sending_time = unpack_from("<Q", mdp_packet, offset=4)[0]

        self.stream_sequence_number = sequence_number
        self.sending_time = sending_time

        for mdp_message in self.mdp_parser.parse(mdp_packet, offset=12):
            self.handle_message(sequence_number, sending_time, mdp_message)

    def handle_message(self, stream_sequence_number, sending_time, mdp_message):
        # We only care about the incremental refresh book packets at this point
        if mdp_message.template_id.value != 32:
            return

        self.handle_incremental(stream_sequence_number, sending_time, mdp_message)

    def handle_incremental(self, stream_sequence_number, sending_time, incremental_message):
        dirty_books = []
        for md_entry in incremental_message.no_md_entries:
            md_entry_price = md_entry.md_entry_px.value
            md_entry_size = md_entry.md_entry_size.value
            security_id = md_entry.security_id.value
            rpt_sequence = md_entry.rpt_seq.value
            number_of_orders = md_entry.number_of_orders.value
            md_price_level = md_entry.md_price_level.value
            md_update_action = md_entry.md_update_action.value
            md_entry_type = md_entry.md_entry_type.value

            if self.security_id_filter and security_id not in self.security_id_filter:
                continue

            if security_id not in self.base_orderbooks:
                self.base_orderbooks[security_id] = OrderBook(security_id)

            orderbook = self.base_orderbooks[security_id]
            dirty = orderbook.update(md_entry_type, md_update_action, stream_sequence_number, sending_time,
                                     rpt_sequence, md_price_level, md_entry_price, md_entry_size,
                                     number_of_orders)

            if dirty and orderbook not in dirty_books:
                dirty_books.append(orderbook)

        if self.orderbook_handler and getattr(self.orderbook_handler, 'on_orderbook'):
            for orderbook in dirty_books:
                self.orderbook_handler.on_orderbook(orderbook)


class OrderBookConsolePrinter(object):
    def on_orderbook(self, orderbook):
        print str(orderbook)


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
    book_builder = OrderBookBuilder(mdp_parser, security_id_filter=security_id_filter)

    console_printer = OrderBookConsolePrinter()
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
                        book_builder.handle_packet(data)
                    except Exception:
                        continue


def process_command_line():
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description="Parse a pcap file containing CME MDP3 market data based on a SBE xml schema file.",
        version="0.1")

    parser.add_argument("pcapfile",
        help="Name of the pcap file to process")

    parser.add_argument("-s", "--schema", default='templates_FixBinary.xml',
        help="Name of the SBE schema xml file")

    parser.add_argument("-i", "--ids", default='',
        help="Comma separated list of security ids to display books for")

    args = parser.parse_args()

    # check number of arguments, verify values, etc.:
    if not os.path.isfile(args.schema):
        parser.error("sbe schema xml file '{}' not found".format(args.schema))

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
