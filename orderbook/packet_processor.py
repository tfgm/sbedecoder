from struct import unpack_from
from orderbook import OrderBook

class PacketProcessor(object):
    def __init__(self, mdp_parser, secdef, security_id_filter=None):
        self.mdp_parser = mdp_parser
        self.secdef = secdef
        self.security_id_filter = security_id_filter

        self.stream_sequence_number = -1  # Note: currently only handles a single stream
        self.sending_time = None

        self.orderbook_handler = None

        # We only keep track of the base books, implieds aren't handled
        self.base_orderbooks = {}

    def handle_packet(self, received_time, mdp_packet):
        sequence_number = unpack_from('<i', mdp_packet, offset=0)[0]
        if sequence_number <= self.stream_sequence_number:
            # already have seen this packet
            return

        if self.stream_sequence_number + 1 <> sequence_number:
            print('warning: stream sequence gap from {} to {}'.format(self.stream_sequence_number, sequence_number))

        sending_time = unpack_from('<Q', mdp_packet, offset=4)[0]

        self.stream_sequence_number = sequence_number
        self.sending_time = sending_time

        for mdp_message in self.mdp_parser.parse(mdp_packet, offset=12):
            self.handle_message(sequence_number, sending_time, received_time, mdp_message)

    def handle_message(self, stream_sequence_number, sending_time, received_time, mdp_message):
        # We only care about the incremental refresh book packets at this point
        if mdp_message.template_id.value == 32:
            self.handle_incremental_refresh_book(stream_sequence_number, sending_time, received_time, mdp_message)
        elif mdp_message.template_id.value == 42:
            self.handle_incremental_refresh_trade_summary(stream_sequence_number, sending_time, received_time, mdp_message)

    def handle_incremental_refresh_book(self, stream_sequence_number, sending_time, received_time, incremental_message):
        updated_books = set()  # Note: we batch all the updates from a single packet into one update
        for md_entry in incremental_message.no_md_entries:

            security_id = md_entry.security_id.value
            if self.security_id_filter and security_id not in self.security_id_filter:
                continue

            if security_id not in self.base_orderbooks:
                security_info = self.secdef.lookup_security_id(security_id)
                if security_info:
                    symbol, depth = security_info
                    ob = OrderBook(security_id, depth, symbol)
                    self.base_orderbooks[security_id] = ob
                else:
                    # Can't properly handle an orderbook without knowing the depth
                    self.base_orderbooks[security_id] = None

            orderbook = self.base_orderbooks[security_id]
            if not orderbook:
                return

            md_entry_price = md_entry.md_entry_px.value
            md_entry_size = md_entry.md_entry_size.value
            rpt_sequence = md_entry.rpt_seq.value
            number_of_orders = md_entry.number_of_orders.value
            md_price_level = md_entry.md_price_level.value
            md_update_action = md_entry.md_update_action.value
            md_entry_type = md_entry.md_entry_type.value

            visible_updated = orderbook.handle_update(sending_time, received_time, stream_sequence_number, rpt_sequence,
                md_price_level, md_entry_type, md_update_action, md_entry_price, md_entry_size, number_of_orders)

            if visible_updated:
                updated_books.add(orderbook)

        if self.orderbook_handler and getattr(self.orderbook_handler, 'on_orderbook'):
            for orderbook in updated_books:
                self.orderbook_handler.on_orderbook(orderbook)

    def handle_incremental_refresh_trade_summary(self, stream_sequence_number, sending_time, received_time, incremental_message):
        for md_entry in incremental_message.no_md_entries:

            security_id = md_entry.security_id.value
            if self.security_id_filter and security_id not in self.security_id_filter:
                continue

            if security_id not in self.base_orderbooks:
                security_info = self.secdef.lookup_security_id(security_id)
                if security_info:
                    symbol, depth = security_info
                    self.base_orderbooks[security_id] = OrderBook(security_id, depth, symbol)
                else:
                    # Can't properly handle an orderbook without knowing the depth
                    self.base_orderbooks[security_id] = None

            orderbook = self.base_orderbooks[security_id]
            if not orderbook:
                return

            md_entry_price = md_entry.md_entry_px.value
            md_entry_size = md_entry.md_entry_size.value
            rpt_sequence = md_entry.rpt_seq.value
            aggressor_side = md_entry.aggressor_side.value
            number_of_orders = md_entry.number_of_orders.value

            orderbook.handle_trade(sending_time, received_time, stream_sequence_number, rpt_sequence,
                md_entry_price, md_entry_size, aggressor_side)

            if self.orderbook_handler and getattr(self.orderbook_handler, 'on_trade'):
                self.orderbook_handler.on_trade(orderbook)
