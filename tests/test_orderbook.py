#!/usr/bin/env python

import urllib
import tempfile
import os

import nose
from nose.tools import assert_equals
from nose.tools import assert_is_instance
from nose.tools import assert_is_none
from nose.tools import assert_is_not_none
from nose.tools import assert_true

from orderbook import OrderBook


class TestOrderBook:

    def setup(self):
        self.book = OrderBook(9999, 3, 'TEST')
        self.book.change(3, 'Offer', 8, 8, 8)
        self.book.change(2, 'Offer', 7, 7, 7)
        self.book.change(1, 'Offer', 6, 6, 6)
        self.book.change(1, 'Bid', 3, 3, 3)
        self.book.change(2, 'Bid', 2, 2, 2)
        self.book.change(3, 'Bid', 1, 1, 1)

        self.book.instrument_sequence = 0

    def teardown(self):
        self.book = None

    def test_adding_level_1_entries(self):
        # def add(self, level, side, price, size, num_orders):
        self.book.add(1, 'Offer', 5, 5, 5)
        self.book.add(1, 'Bid', 4, 4, 4)

        assert_equals(self.book.offers[0].price, 5)
        assert_equals(self.book.offers[2].price, 7)

        assert_equals(self.book.bids[0].price, 4)
        assert_equals(self.book.bids[2].price, 2)

    def test_adding_level_3_entries(self):
        # def add(self, level, side, price, size, num_orders):
        self.book.add(3, 'Offer', 9, 9, 9)
        self.book.add(3, 'Bid', 0, 0, 0)

        assert_equals(self.book.offers[0].price, 6)
        assert_equals(self.book.offers[2].price, 9)

        assert_equals(self.book.bids[0].price, 3)
        assert_equals(self.book.bids[2].price, 0)

    def test_deleting_level_1_entries(self):
        # def add(self, level, side, price, size, num_orders):
        self.book.delete(1, 'Offer')
        self.book.delete(1, 'Bid')

        assert_equals(self.book.offers[0].price, 7)
        assert_is_none(self.book.offers[2].price)

        assert_equals(self.book.bids[0].price, 2)
        assert_is_none(self.book.bids[2].price)

    def test_deleting_level_3_entries(self):
        # def add(self, level, side, price, size, num_orders):
        self.book.delete(3, 'Offer')
        self.book.delete(3, 'Bid')

        assert_equals(self.book.offers[0].price, 6)
        assert_is_none(self.book.offers[2].price)

        assert_equals(self.book.bids[0].price, 3)
        assert_is_none(self.book.bids[2].price)

    def test_change(self):
        self.book.change(3, 'Offer', 8, 8, 8)
        assert_equals(self.book.offers[2].price, 8)
        assert_equals(self.book.offers[2].size, 8)
        assert_equals(self.book.offers[2].num_orders, 8)

        self.book.change(1, 'Bid', 4, 4, 4)
        assert_equals(self.book.bids[0].price, 4)
        assert_equals(self.book.bids[0].size, 4)
        assert_equals(self.book.bids[0].num_orders, 4)

#def update(self, sending_time,  received_time,  stream_sequence, instrument_sequence, level, md_entry_type, md_update_action, price, size, num_orders):
    def test_update_book_change(self):

        self.book.handle_update(101, 102, 1, 1, 3, 'Offer', 'Change', 8, 8, 8)

        assert_equals(self.book.offers[0].price, 6)
        assert_equals(self.book.offers[0].size, 6)
        assert_equals(self.book.offers[0].num_orders, 6)

        assert_equals(self.book.offers[2].price, 8)
        assert_equals(self.book.offers[2].size, 8)
        assert_equals(self.book.offers[2].num_orders, 8)

        self.book.handle_update(101, 102, 2, 2, 1, 'Bid', 'Change', 4, 4, 4)

        assert_equals(self.book.bids[0].price, 4)
        assert_equals(self.book.bids[0].size, 4)
        assert_equals(self.book.bids[0].num_orders, 4)

        assert_equals(self.book.bids[2].price, 1)
        assert_equals(self.book.bids[2].size, 1)
        assert_equals(self.book.bids[2].num_orders, 1)

    def test_update_book_add(self):

        self.book.handle_update(101, 102, 1, 1, 1, 'Offer', 'New', 5, 5, 5)

        assert_equals(self.book.offers[0].price, 5)
        assert_equals(self.book.offers[0].size, 5)
        assert_equals(self.book.offers[0].num_orders, 5)

        assert_equals(self.book.offers[2].price, 7)
        assert_equals(self.book.offers[2].size, 7)
        assert_equals(self.book.offers[2].num_orders, 7)

        self.book.handle_update(101, 102, 2, 2, 1, 'Bid', 'New', 4, 4, 4)

        assert_equals(self.book.bids[0].price, 4)
        assert_equals(self.book.bids[0].size, 4)
        assert_equals(self.book.bids[0].num_orders, 4)

        assert_equals(self.book.bids[2].price, 2)
        assert_equals(self.book.bids[2].size, 2)
        assert_equals(self.book.bids[2].num_orders, 2)


    def test_update_book_delete(self):
        self.book.handle_update(101, 102, 1, 1, 1, 'Offer', 'Delete', None, None, None)

        assert_equals(self.book.offers[0].price, 7)
        assert_equals(self.book.offers[0].size, 7)
        assert_equals(self.book.offers[0].num_orders, 7)
        assert_is_none(self.book.offers[2].price)

        self.book.handle_update(101, 102, 2, 2, 1, 'Bid',  'Delete', None, None, None)
        assert_equals(self.book.bids[0].price, 2)
        assert_equals(self.book.bids[0].size, 2)
        assert_equals(self.book.bids[0].num_orders, 2)
        assert_is_none(self.book.bids[2].price)

    def test_update_book_old_sequence(self):
        self.book.instrument_sequence = 99
        self.book.handle_update(101, 102, 100, 100, 1, 'Offer', 'New', 5, 5, 5)
        self.book.handle_update(101, 102, 99, 99, 1, 'Offer', 'New', 999, 999, 999)

        assert_equals(self.book.offers[0].price, 5)
        assert_equals(self.book.offers[0].size, 5)
        assert_equals(self.book.offers[0].num_orders, 5)

        assert_equals(self.book.offers[2].price, 7)
        assert_equals(self.book.offers[2].size, 7)
        assert_equals(self.book.offers[2].num_orders, 7)

        self.book.instrument_sequence = 99
        self.book.handle_update(101, 102, 100, 100, 1, 'Bid', 'New', 4, 4, 4)
        self.book.handle_update(101, 102, 99, 99, 1, 'Bid', 'New', 999, 999, 999)

        assert_equals(self.book.bids[0].price, 4)
        assert_equals(self.book.bids[0].size, 4)
        assert_equals(self.book.bids[0].num_orders, 4)

        assert_equals(self.book.bids[2].price, 2)
        assert_equals(self.book.bids[2].size, 2)
        assert_equals(self.book.bids[2].num_orders, 2)

    def test_update_book_duplicate_sequence(self):
        self.book.handle_update(101, 102, 1, 1, 1, 'Offer', 'New', 5, 5, 5)
        self.book.handle_update(101, 102, 1, 1, 1, 'Offer', 'New', 999, 999, 999)

        assert_equals(self.book.offers[0].price, 5)
        assert_equals(self.book.offers[0].size, 5)
        assert_equals(self.book.offers[0].num_orders, 5)

        assert_equals(self.book.offers[2].price, 7)
        assert_equals(self.book.offers[2].size, 7)
        assert_equals(self.book.offers[2].num_orders, 7)

        self.book.handle_update(101, 102, 2, 2, 1, 'Bid', 'New', 4, 4, 4)
        self.book.handle_update(101, 102, 2, 2, 1, 'Bid', 'New', 999, 999, 999)

        assert_equals(self.book.bids[0].price, 4)
        assert_equals(self.book.bids[0].size, 4)
        assert_equals(self.book.bids[0].num_orders, 4)

        assert_equals(self.book.bids[2].price, 2)
        assert_equals(self.book.bids[2].size, 2)
        assert_equals(self.book.bids[2].num_orders, 2)

    def test_update_book_gapped(self):
        return  # not ready for testing gaps until we handle more messages
'''
        self.book.handle_update(101, 102, 1, 1, 3, 'Offer', 'Change', 8, 8, 8)
        self.book.handle_update(101, 102, 1, 2, 2, 'Offer', 'Change', 7, 7, 7)
        self.book.handle_update(101, 102, 1, 3, 1, 'Offer', 'Change', 6, 6, 6)
        self.book.handle_update(101, 102, 99, 99, 1, 'Offer', 'Change', 999, 999, 999)

        assert_equals(self.book.offers[0].price, 999)
        assert_equals(self.book.offers[0].size, 999)
        assert_equals(self.book.offers[0].num_orders, 999)

        assert_is_none(self.book.offers[1].price)
        assert_is_none(self.book.offers[1].size)
        assert_is_none(self.book.offers[1].num_orders)

        assert_is_none(self.book.bids[0].price)
        assert_is_none(self.book.bids[0].size)
        assert_is_none(self.book.bids[0].num_orders)
'''

if __name__ == '__main__':
    nose.runmodule()
