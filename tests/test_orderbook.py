#!/usr/bin/env python

import pytest

from mdp.orderbook import OrderBook


@pytest.fixture()
def book():
    book = OrderBook(9999, 3, 'TEST')
    book.change(3, 'Offer', 8, 8, 8)
    book.change(2, 'Offer', 7, 7, 7)
    book.change(1, 'Offer', 6, 6, 6)
    book.change(1, 'Bid', 3, 3, 3)
    book.change(2, 'Bid', 2, 2, 2)
    book.change(3, 'Bid', 1, 1, 1)

    book.instrument_sequence = 0

    return book


def test_adding_level_1_entries(book):
    # def add(self, level, side, price, size, num_orders):
    book.add(1, 'Offer', 5, 5, 5)
    book.add(1, 'Bid', 4, 4, 4)

    assert book.offers[0].price == 5
    assert book.offers[2].price == 7

    assert book.bids[0].price == 4
    assert book.bids[2].price == 2


def test_adding_level_3_entries(book):
    # def add(self, level, side, price, size, num_orders):
    book.add(3, 'Offer', 9, 9, 9)
    book.add(3, 'Bid', 0, 0, 0)

    assert book.offers[0].price == 6
    assert book.offers[2].price == 9

    assert book.bids[0].price == 3
    assert book.bids[2].price == 0


def test_deleting_level_1_entries(book):
    # def add(self, level, side, price, size, num_orders):
    book.delete(1, 'Offer')
    book.delete(1, 'Bid')

    assert book.offers[0].price == 7
    assert book.offers[2].price is None

    assert book.bids[0].price == 2
    assert book.bids[2].price is None


def test_deleting_level_3_entries(book):
    # def add(self, level, side, price, size, num_orders):
    book.delete(3, 'Offer')
    book.delete(3, 'Bid')

    assert book.offers[0].price == 6
    assert book.offers[2].price is None

    assert book.bids[0].price == 3
    assert book.bids[2].price is None


def test_change(book):
    book.change(3, 'Offer', 8, 8, 8)
    assert book.offers[2].price == 8
    assert book.offers[2].size == 8
    assert book.offers[2].num_orders == 8

    book.change(1, 'Bid', 4, 4, 4)
    assert book.bids[0].price == 4
    assert book.bids[0].size == 4
    assert book.bids[0].num_orders == 4


def test_update_book_change(book):
    book.handle_update(
        sending_time=101,
        received_time=102,
        stream_sequence=1,
        instrument_sequence=1,
        level=3,
        md_entry_type='Offer',
        md_update_action='Change',
        price=8,
        size=8,
        num_orders=8
    )

    assert book.offers[0].price == 6
    assert book.offers[0].size == 6
    assert book.offers[0].num_orders == 6

    assert book.offers[2].price == 8
    assert book.offers[2].size == 8
    assert book.offers[2].num_orders == 8

    book.handle_update(101, 102, 2, 2, 1, 'Bid', 'Change', 4, 4, 4)

    assert book.bids[0].price == 4
    assert book.bids[0].size == 4
    assert book.bids[0].num_orders == 4

    assert book.bids[2].price == 1
    assert book.bids[2].size == 1
    assert book.bids[2].num_orders == 1


def test_update_book_add(book):
    book.handle_update(101, 102, 1, 1, 1, 'Offer', 'New', 5, 5, 5)

    assert book.offers[0].price == 5
    assert book.offers[0].size == 5
    assert book.offers[0].num_orders == 5

    assert book.offers[2].price == 7
    assert book.offers[2].size == 7
    assert book.offers[2].num_orders == 7

    book.handle_update(101, 102, 2, 2, 1, 'Bid', 'New', 4, 4, 4)

    assert book.bids[0].price == 4
    assert book.bids[0].size == 4
    assert book.bids[0].num_orders == 4

    assert book.bids[2].price == 2
    assert book.bids[2].size == 2
    assert book.bids[2].num_orders == 2


def test_update_book_delete(book):
    book.handle_update(101, 102, 1, 1, 1, 'Offer', 'Delete', None, None, None)

    assert book.offers[0].price == 7
    assert book.offers[0].size == 7
    assert book.offers[0].num_orders == 7
    assert book.offers[2].price is None

    book.handle_update(101, 102, 2, 2, 1, 'Bid', 'Delete', None, None, None)
    assert book.bids[0].price == 2
    assert book.bids[0].size == 2
    assert book.bids[0].num_orders == 2
    assert book.bids[2].price is None


def test_update_book_old_sequence(book):
    book.instrument_sequence = 99
    book.handle_update(101, 102, 100, 100, 1, 'Offer', 'New', 5, 5, 5)
    book.handle_update(101, 102, 99, 99, 1, 'Offer', 'New', 999, 999, 999)

    assert book.offers[0].price == 5
    assert book.offers[0].size == 5
    assert book.offers[0].num_orders == 5

    assert book.offers[2].price == 7
    assert book.offers[2].size == 7
    assert book.offers[2].num_orders == 7

    book.instrument_sequence = 99
    book.handle_update(101, 102, 100, 100, 1, 'Bid', 'New', 4, 4, 4)
    book.handle_update(101, 102, 99, 99, 1, 'Bid', 'New', 999, 999, 999)

    assert book.bids[0].price == 4
    assert book.bids[0].size == 4
    assert book.bids[0].num_orders == 4

    assert book.bids[2].price == 2
    assert book.bids[2].size == 2
    assert book.bids[2].num_orders == 2


def test_update_book_duplicate_sequence(book):
    book.handle_update(101, 102, 1, 1, 1, 'Offer', 'New', 5, 5, 5)
    book.handle_update(101, 102, 1, 1, 1, 'Offer', 'New', 999, 999, 999)

    assert book.offers[0].price == 5
    assert book.offers[0].size == 5
    assert book.offers[0].num_orders == 5

    assert book.offers[2].price == 7
    assert book.offers[2].size == 7
    assert book.offers[2].num_orders == 7

    book.handle_update(101, 102, 2, 2, 1, 'Bid', 'New', 4, 4, 4)
    book.handle_update(101, 102, 2, 2, 1, 'Bid', 'New', 999, 999, 999)

    assert book.bids[0].price == 4
    assert book.bids[0].size == 4
    assert book.bids[0].num_orders == 4

    assert book.bids[2].price == 2
    assert book.bids[2].size == 2
    assert book.bids[2].num_orders == 2


def test_update_book_gapped(book):
    """
    book.handle_update(101, 102, 1, 1, 3, 'Offer', 'Change', 8, 8, 8)
    book.handle_update(101, 102, 1, 2, 2, 'Offer', 'Change', 7, 7, 7)
    book.handle_update(101, 102, 1, 3, 1, 'Offer', 'Change', 6, 6, 6)
    book.handle_update(101, 102, 99, 99, 1, 'Offer', 'Change', 999, 999, 999)

    assert_equals(book.offers[0].price, 999)
    assert_equals(book.offers[0].size, 999)
    assert_equals(book.offers[0].num_orders, 999)

    assert_is_none(book.offers[1].price)
    assert_is_none(book.offers[1].size)
    assert_is_none(book.offers[1].num_orders)

    assert_is_none(book.bids[0].price)
    assert_is_none(book.bids[0].size)
    assert_is_none(book.bids[0].num_orders)
    """

    pass  # not ready for testing gaps until we handle more messages
