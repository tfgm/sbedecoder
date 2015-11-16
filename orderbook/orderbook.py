class OrderBookEntry(object):
    def __init__(self):
        self.price = None
        self.size = None
        self.num_orders = None

    def __str__(self):
        return '({}) {}@{}'.format(self.num_orders, self.size, self.price,)


class OrderBook(object):
    def __init__(self, security_id, levels, description):
        self.security_id = security_id
        self.levels = levels
        self.display_levels = levels
        self.description = description
        self.sending_time = None
        self.received_time = None
        self.stream_sequence = -1
        self.instrument_sequence = -1
        self.last_price = None
        self.last_size = None
        self.last_aggressor_side = None
        self.bids = []
        self.offers = []
        for i in range(0, self.levels):
            self.bids.append(OrderBookEntry())
            self.offers.append(OrderBookEntry())

    def invalidate(self):
        self.sending_time = None
        self.received_time = None
        self.stream_sequence = -1
        self.instrument_sequence = -1
        self.bids = []
        self.offers = []
        for i in range(0, self.levels):
            self.bids.append(OrderBookEntry())
            self.offers.append(OrderBookEntry())

    def have_seen_sequence(self, instrument_sequence):
        return instrument_sequence <= self.instrument_sequence

    def is_gapped_sequence(self, instrument_sequence):
        return False  # can't detect gaps until we handle trades, volume, statistics and implied messages
        # return instrument_sequence > self.instrument_sequence + 1

    def _update_book_keeping(self, sending_time, received_time, stream_sequence, instrument_sequence):
        if self.is_gapped_sequence(instrument_sequence):
            self.invalidate()
        self.sending_time = sending_time
        self.received_time = received_time
        self.stream_sequence = stream_sequence
        self.instrument_sequence = instrument_sequence

    def add(self, level, side, price, size, num_orders):
        entries = self.bids if side == 'Bid' else self.offers
        order_book_entry = OrderBookEntry()
        order_book_entry.price = price
        order_book_entry.size = size
        order_book_entry.num_orders = num_orders
        entries.insert(level-1, order_book_entry)
        entries.pop()  # delete the last item from the list

    def change(self, level, side, price, size, num_orders):
        entries = self.bids if side == 'Bid' else self.offers
        order_book_entry = entries[level-1]
        order_book_entry.price = price
        order_book_entry.size = size
        order_book_entry.num_orders = num_orders

    def delete(self, level, side):
        entries = self.bids if side == 'Bid' else self.offers
        del entries[level-1]
        entries.append(OrderBookEntry())  # replace the deleted item with a new one

    def handle_update(self, sending_time, received_time, stream_sequence, instrument_sequence,
               level, md_entry_type, md_update_action, price, size, num_orders):

        if self.have_seen_sequence(instrument_sequence):
            return False

        # We only care about outright changes for now
        if md_entry_type not in ['Bid', 'Offer']:
            return False

        if md_update_action not in ['Change', 'New', 'Delete']:
            return False

        self._update_book_keeping(sending_time,  received_time, stream_sequence, instrument_sequence)

        if md_update_action == 'New':
            self.add(level, md_entry_type, price, size, num_orders)
        elif md_update_action == 'Change':
            self.change(level, md_entry_type, price, size, num_orders)
        elif md_update_action == 'Delete':
            self.delete(level, md_entry_type)

        # return True if the update was relevant (occurred within the display_levels)
        return True if level <= self.display_levels else False

    def handle_trade(self, sending_time, received_time, stream_sequence, instrument_sequence,
            price, size, aggressor_side):

        if self.have_seen_sequence(instrument_sequence):
            return False

        self._update_book_keeping(sending_time,  received_time, stream_sequence, instrument_sequence)

        self.last_price = price
        self.last_size = size
        self.last_aggressor_side = aggressor_side

    def __str__(self):
        delta = None
        if self.sending_time is not None and self.received_time is not None :
            delta = self.received_time - (self.sending_time/1000)
        result = '{} ({}) SSN:{} ISN:{} Sent:{} Received:{} ({})\n'.format(
            self.description, self.security_id, self.stream_sequence, self.instrument_sequence,
            self.sending_time, self.received_time, delta)
        for i in range(0, self.display_levels):
            entry = self.bids[i]
            bid_string = '({:>6}) {:>6} - {:>12}'.format(entry.num_orders, entry.size, entry.price)
            entry = self.offers[i]
            offer_string = '{:<12} - {:<6} ({:<6}) '.format(entry.price, entry.size, entry.num_orders)
            result += '{}|{}\n'.format(bid_string, offer_string)
        return result


class ConsolePrinter(object):
    def on_orderbook(self, orderbook):
        print(str(orderbook))
    def on_trade(self, orderbook):
        print('{} ({}) SSN:{} ISN:{} Sent:{} Received:{} Trade - {} @ {} ({})\n'.format(
            orderbook.description, orderbook.security_id, orderbook.stream_sequence, orderbook.instrument_sequence,
            orderbook.sending_time, orderbook.received_time, orderbook.last_size, orderbook.last_price,
            orderbook.last_aggressor_side))



