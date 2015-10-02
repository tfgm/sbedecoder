#!/usr/bin/env python

import nose
import urllib
import tempfile
import os
from sbedecoder import SBESchema
from sbedecoder import SBEMessageFactory
from sbedecoder import SBEParser
from nose.tools import assert_equals


class TestSBEParserLibrary:

    SCHEMA_URL = 'ftp://ftp.cmegroup.com/SBEFix/Production/Templates/templates_FixBinary.xml'
    LOCAL_TEMPLATE_FILENAME = None

    def __init__(self):
        self.recorded_messages = None

    @classmethod
    def setup_class(cls):
        TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME = tempfile.NamedTemporaryFile().name
        urllib.urlretrieve(TestSBEParserLibrary.SCHEMA_URL, TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)

    @classmethod
    def teardown_class(cls):
        os.remove(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)

    def setup(self):
        self.recorded_messages = []

    def test_security_status_reset_statistics(self):
        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = 'M\x7f\xcc\x04<}\x94\x89\x02\x89\xf5\x13(\x00\x1e\x00\x1e\x00\x01\x00\x05\x00\x9a\x94x\x89\x02\x89\xf5\x1309\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\x7f\x06A\x00\x02\x00\x04'
        offset = 12

        for message in parser.parse(msg_buffer, offset):
            self.recorded_messages.append(message)

        # Validate that we parsed a security status message
        assert_equals(1, len(self.recorded_messages))
        recorded_message = self.recorded_messages[0]
        assert_equals(30, recorded_message.template_id.value)
        assert_equals('SecurityStatus', recorded_message.name)
        assert_equals(16646, recorded_message.trade_date.value)
        assert_equals(1438206300004062362, recorded_message.transact_time.value)
        assert_equals('Reset Statistics', recorded_message.security_trading_event.value)
        assert_equals('Trading Halt', recorded_message.security_trading_status.value)
        assert_equals('09', recorded_message.security_group.value)
        assert_equals('', recorded_message.asset.value)
        assert_equals('Group Schedule', recorded_message.halt_reason.value)
        assert_equals(None, recorded_message.security_id.value)

    def test_security_status(self):
        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = 'N\x7f\xcc\x04F\x9a\x95\x89\x02\x89\xf5\x13(\x00\x1e\x00\x1e\x00\x01\x00\x05\x00\x9a\x94x\x89\x02\x89\xf5\x13CT\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\x7f\x06A\x00\x02\x00\x04'
        offset = 12

        for message in parser.parse(msg_buffer, offset):
            self.recorded_messages.append(message)

        # Validate that we parsed a security status message
        assert_equals(1, len(self.recorded_messages))
        recorded_message = self.recorded_messages[0]
        assert_equals(30, recorded_message.template_id.value)
        assert_equals('SecurityStatus', recorded_message.name)
        assert_equals(16646, recorded_message.trade_date.value)
        assert_equals(1438206300004062362, recorded_message.transact_time.value)
        assert_equals('Reset Statistics', recorded_message.security_trading_event.value)
        assert_equals('Trading Halt', recorded_message.security_trading_status.value)
        assert_equals('CT', recorded_message.security_group.value)
        assert_equals('', recorded_message.asset.value)
        assert_equals('Group Schedule', recorded_message.halt_reason.value)
        assert_equals(None, recorded_message.security_id.value)

    def test_incremental_refresh_multiple_messages(self):

        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = 'U[\xe0\x02\xd6\t\xc64Z%\xe6\x138\x00\x0b\x00 \x00\x01\x00\x05\x00yR\xc44Z%\xe6\x13\x04\x00\x00 \x00\x01\x80\x97\x1d\x94\xff\xff\xff\xff\r\x00\x00\x00\xcb\xb5\x00\x00\x1f%\x0e\x00\x07\x00\x00\x00\n\x011\x00\x00\x00\x00\x00\x18\x00\x0b\x00 \x00\x01\x00\x05\x00yR\xc44Z%\xe6\x13\x80\x00\x00 \x00\x00'
        offset = 12

        msg_count = 0
        for message in parser.parse(msg_buffer, offset):
            msg_count += 1

            if msg_count == 1:
                assert_equals(32, message.template_id.value)
                assert_equals(1433874600726647417, message.transact_time.value)
                assert_equals(4, message.match_event_indicator.raw_value)
                assert_equals('LastQuoteMsg', message.match_event_indicator.value)

                repeating_groups = [x for x in message.no_md_entries]
                assert_equals(1, len(repeating_groups))
                repeating_group = repeating_groups[0]
                assert_equals(-181.0, repeating_group.md_entry_px.value)
                assert_equals(13, repeating_group.md_entry_size.value)
                assert_equals(46539, repeating_group.security_id.value)
                assert_equals(927007, repeating_group.rpt_seq.value)
                assert_equals(7, repeating_group.number_of_orders.value)
                assert_equals(10, repeating_group.md_price_level.value)
                assert_equals(1, repeating_group.md_update_action.raw_value)
                assert_equals('Change', repeating_group.md_update_action.value)
                assert_equals('1', repeating_group.md_entry_type.raw_value)
                assert_equals('Offer', repeating_group.md_entry_type.value)
            elif msg_count == 2:
                assert_equals(32, message.template_id.value)
                assert_equals(1433874600726647417, message.transact_time.value)
                assert_equals(128, message.match_event_indicator.raw_value)
                assert_equals('EndOfEvent', message.match_event_indicator.value)

                # No repeating groups in this message
                repeating_groups = [x for x in message.no_md_entries]
                assert_equals(0, len(repeating_groups))

        assert_equals(2, msg_count)

    def test_incremental_refresh_trade_summary(self):

        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = 'rWa\x00\xdc"\xda6Z%\xe6\x13`\x00\x0b\x00*\x00\x01\x00\x05\x00\x05\xd0\xd46Z%\xe6\x13\x01\x00\x00 \x00\x01\x80_\x8f\x9e\x06\x00\x00\x00\x01\x00\x00\x00.\xee\x01\x00\xee\xe4\x1b\x00\x02\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x10\x00\x00\x00\x00\x00\x00\x02\xca\x89>\x0e\xb6\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00'
        offset = 12

        msg_count = 0
        for message in parser.parse(msg_buffer, offset):
            msg_count += 1
            assert_equals(42, message.template_id.value)
            assert_equals(1433874600761282565, message.transact_time.value)
            assert_equals(1, message.match_event_indicator.raw_value)
            assert_equals('LastTradeMsg', message.match_event_indicator.value)

            # This message has two repeating groups
            assert_equals(2, len(message.iterators))

            # We expect only 1 md entry
            for md_entry in message.no_md_entries:
                assert_equals(2843.0, md_entry.md_entry_px.value)
                assert_equals(1, md_entry.md_entry_size.value)
                assert_equals(126510, md_entry.security_id.value)
                assert_equals(1828078, md_entry.rpt_seq.value)
                assert_equals(2, md_entry.number_of_orders.value)
                assert_equals(2, md_entry.aggressor_side.raw_value)
                assert_equals('Sell', md_entry.aggressor_side.value)
                assert_equals(0, md_entry.md_update_action.raw_value)
                assert_equals('New', md_entry.md_update_action.value)
                assert_equals('2', md_entry.md_entry_type.value)

            # We expect two trades in this message
            num_order_id_entries = 0
            for order_id_entry in message.no_order_id_entries:
                num_order_id_entries += 1
                if num_order_id_entries == 1:
                    assert_equals(781923027402, order_id_entry.order_id.value)
                    assert_equals(1, order_id_entry.last_qty.value)
                else:
                    assert_equals(0, order_id_entry.order_id.value)
                    assert_equals(1, order_id_entry.last_qty.value)

        assert_equals(1, msg_count)


if __name__ == "__main__":
    nose.runmodule()


