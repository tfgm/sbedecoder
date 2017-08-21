#!/usr/bin/env python

import nose
import urllib
import tempfile
import os
import binascii
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
        try:
            from sbedecoder.generated import __messages__ as generated_messages
            schema.load(generated_messages)
        except:
            schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)

        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = binascii.a2b_hex('5603a9009c16d545349ad91428001e001e000100080003259845349ad914455300000000000000000000ffffff7fed4380150004')

        offset = 12

        for message in parser.parse(msg_buffer, offset):
            self.recorded_messages.append(message)

        # Validate that we parsed a security status message
        assert_equals(1, len(self.recorded_messages))
        recorded_message = self.recorded_messages[0]
        assert_equals(30, recorded_message.template_id.value)
        assert_equals('SecurityStatus', recorded_message.name)
        assert_equals(17389, recorded_message.trade_date.value)
        assert_equals(1502401500001346819, recorded_message.transact_time.value)
        assert_equals('Reset Statistics', recorded_message.security_trading_event.value)
        assert_equals('Pre Open', recorded_message.security_trading_status.value)
        assert_equals('ES', recorded_message.security_group.value)
        assert_equals('', recorded_message.asset.value)
        assert_equals('Group Schedule', recorded_message.halt_reason.value)
        assert_equals(None, recorded_message.security_id.value)

    def test_security_status(self):
        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = binascii.a2b_hex('1409a900bbe7b5d5fe9ad91428001e001e000100080019989cd5fe9ad914455300000000000000000000ffffff7fed4380150001')
        offset = 12

        for message in parser.parse(msg_buffer, offset):
            self.recorded_messages.append(message)

        # Validate that we parsed a security status message
        assert_equals(1, len(self.recorded_messages))
        recorded_message = self.recorded_messages[0]
        assert_equals(30, recorded_message.template_id.value)
        assert_equals('SecurityStatus', recorded_message.name)
        assert_equals(17389, recorded_message.trade_date.value)
        assert_equals(1502402370000951321, recorded_message.transact_time.value)
        assert_equals('EndOfEvent', recorded_message.match_event_indicator.value)
        assert_equals('Pre Open', recorded_message.security_trading_status.value)
        assert_equals('ES', recorded_message.security_group.value)
        assert_equals('', recorded_message.asset.value)
        assert_equals('Group Schedule', recorded_message.halt_reason.value)
        assert_equals(None, recorded_message.security_id.value)
        assert_equals('No Cancel', recorded_message.security_trading_event.value)

    def test_incremental_refresh_verify_groups(self):

        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = binascii.a2b_hex(
            'c30fa90082dd3f8b069bd91478000b0020000100080095ab3d8b069bd914840000200002009bb1203602000002000000805d00003e2d140001000000010030000000000080e8ca113602000002000000805d00003f2d140001000000020130000000000018000000000000019c53980a9600000024131444010000000200000001010000')
        offset = 12

        msg_count = 0
        for message in parser.parse(msg_buffer, offset):
            msg_count += 1

            if msg_count == 1:
                assert_equals(32, message.template_id.value)
                assert_equals(1502402403112954773, message.transact_time.value)
                assert_equals(132, message.match_event_indicator.raw_value)
                assert_equals('LastQuoteMsg, EndOfEvent', message.match_event_indicator.value)

                groups = [x for x in message.groups]
                assert_equals(2, len(groups))

                repeating_groups = groups[0].repeating_groups  # no_md_entries

                n = 0
                for repeating_group in repeating_groups:
                    if n == 0:
                        assert_equals(243150.0, repeating_group.md_entry_px.value)
                        assert_equals(2, repeating_group.md_entry_size.value)
                        assert_equals(23936, repeating_group.security_id.value)
                        assert_equals(1322302, repeating_group.rpt_seq.value)
                        assert_equals(1, repeating_group.number_of_orders.value)
                        assert_equals(1, repeating_group.md_price_level.value)
                        assert_equals(0, repeating_group.md_update_action.raw_value)
                        assert_equals('New', repeating_group.md_update_action.value)
                        assert_equals('0', repeating_group.md_entry_type.raw_value)
                        assert_equals('Bid', repeating_group.md_entry_type.value)
                    elif n == 1:
                        assert_equals(243125.0, repeating_group.md_entry_px.value)
                        assert_equals(2, repeating_group.md_entry_size.value)
                        assert_equals(23936, repeating_group.security_id.value)
                        assert_equals(1322303, repeating_group.rpt_seq.value)
                        assert_equals(1, repeating_group.number_of_orders.value)
                        assert_equals(2, repeating_group.md_price_level.value)
                        assert_equals(1, repeating_group.md_update_action.raw_value)
                        assert_equals('Change', repeating_group.md_update_action.value)
                        assert_equals('0', repeating_group.md_entry_type.raw_value)
                        assert_equals('Bid', repeating_group.md_entry_type.value)
                    n += 1
                assert_equals(2, n)

                repeating_groups = groups[1].repeating_groups  # no_order_id_entries

                n = 0
                for repeating_group in repeating_groups:
                    if n == 0:
                        assert_equals(644422849436, repeating_group.order_id.value)
                        assert_equals(5437133604, repeating_group.md_order_priority.value)
                        assert_equals(2, repeating_group.md_display_qty.value)
                        assert_equals(1, repeating_group.reference_id.value)
                        assert_equals('Update', repeating_group.order_update_action.value)
                        assert_equals(1, repeating_group.order_update_action.raw_value)
                    n += 1
                assert_equals(1, n)


    def test_incremental_refresh_verify_group_attributes(self):
        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = binascii.a2b_hex(
            'c30fa90082dd3f8b069bd91478000b0020000100080095ab3d8b069bd914840000200002009bb1203602000002000000805d00003e2d140001000000010030000000000080e8ca113602000002000000805d00003f2d140001000000020130000000000018000000000000019c53980a9600000024131444010000000200000001010000')
        offset = 12

        msg_count = 0
        for message in parser.parse(msg_buffer, offset):
            msg_count += 1

            if msg_count == 1:
                assert_equals(32, message.template_id.value)
                assert_equals(1502402403112954773, message.transact_time.value)
                assert_equals(132, message.match_event_indicator.raw_value)
                assert_equals('LastQuoteMsg, EndOfEvent', message.match_event_indicator.value)

                n = 0
                for repeating_group in message.no_md_entries:
                    if n == 0:
                        assert_equals(243150.0, repeating_group.md_entry_px.value)
                        assert_equals(2, repeating_group.md_entry_size.value)
                        assert_equals(23936, repeating_group.security_id.value)
                        assert_equals(1322302, repeating_group.rpt_seq.value)
                        assert_equals(1, repeating_group.number_of_orders.value)
                        assert_equals(1, repeating_group.md_price_level.value)
                        assert_equals(0, repeating_group.md_update_action.raw_value)
                        assert_equals('New', repeating_group.md_update_action.value)
                        assert_equals('0', repeating_group.md_entry_type.raw_value)
                        assert_equals('Bid', repeating_group.md_entry_type.value)
                    elif n == 1:
                        assert_equals(243125.0, repeating_group.md_entry_px.value)
                        assert_equals(2, repeating_group.md_entry_size.value)
                        assert_equals(23936, repeating_group.security_id.value)
                        assert_equals(1322303, repeating_group.rpt_seq.value)
                        assert_equals(1, repeating_group.number_of_orders.value)
                        assert_equals(2, repeating_group.md_price_level.value)
                        assert_equals(1, repeating_group.md_update_action.raw_value)
                        assert_equals('Change', repeating_group.md_update_action.value)
                        assert_equals('0', repeating_group.md_entry_type.raw_value)
                        assert_equals('Bid', repeating_group.md_entry_type.value)
                    n += 1
                assert_equals(2, n)

                n = 0
                for repeating_group in message.no_order_id_entries:
                    if n == 0:
                        assert_equals(644422849436, repeating_group.order_id.value)
                        assert_equals(5437133604, repeating_group.md_order_priority.value)
                        assert_equals(2, repeating_group.md_display_qty.value)
                        assert_equals(1, repeating_group.reference_id.value)
                        assert_equals('Update', repeating_group.order_update_action.value)
                        assert_equals(1, repeating_group.order_update_action.raw_value)
                    n += 1
                assert_equals(1, n)


    def test_incremental_refresh_multiple_messages(self):

        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = binascii.a2b_hex('c90fa9008a15428b069bd91458000b00200001000800e7c43d8b069bd91484000020000180b2654d360200008e0000000a610000f62fac003000000007013000000000001800000000000001e44c980a960000002b13144401000000010000000101000058000b002000010008006f203f8b069bd9148400002000018017336b3602000004000000805d0000402d140002000000020131000000000018000000000000016153980a960000002c131444010000000200000001010000')
        offset = 12

        msg_count = 0
        for message in parser.parse(msg_buffer, offset):
            if msg_count == 0:
                assert_equals('MDIncrementalRefreshBook', message.name)
                n = 0
                for entry in message.no_md_entries:
                    if n == 0:
                        assert_equals(243225.0, entry.md_entry_px.value)
                        assert_equals(142, entry.md_entry_size.value)
                    n += 1
                assert_equals(1, n)
            elif msg_count == 1:
                assert_equals('MDIncrementalRefreshBook', message.name)
                n = 0
                for entry in message.no_md_entries:
                    if n == 0:
                        assert_equals(243275.0, entry.md_entry_px.value)
                    assert_equals(4, entry.md_entry_size.value)
                    n += 1
                assert_equals(1, n)
            msg_count += 1
        assert_equals(2, msg_count)

    def test_incremental_refresh_trade_summary(self):

        schema = SBESchema()
        schema.parse(TestSBEParserLibrary.LOCAL_TEMPLATE_FILENAME)
        msg_factory = SBEMessageFactory(schema)
        parser = SBEParser(msg_factory)

        msg_buffer = binascii.a2b_hex('2f0aa9007decc6d2059bd91460000b002a000100080085b89fd2059bd91401000020000100f981d336020000020000000a610000fe2aac00020000000100ffffffff000010000000000000023051980a960000000200000000000000ad50980a960000000200000000000000')
        offset = 12

        msg_count = 0
        for message in parser.parse(msg_buffer, offset):
            msg_count += 1
            assert_equals(42, message.template_id.value)
            assert_equals(1502402400015595653, message.transact_time.value)
            assert_equals(1, message.match_event_indicator.raw_value)
            assert_equals('LastTradeMsg', message.match_event_indicator.value)

            # This message has two repeating groups
            assert_equals(2, len(message.groups))

            # We expect only 1 md entry
            for md_entry in message.no_md_entries:
                assert_equals(243450.0, md_entry.md_entry_px.value)
                assert_equals(2, md_entry.md_entry_size.value)
                assert_equals(24842, md_entry.security_id.value)
                assert_equals(11283198, md_entry.rpt_seq.value)
                assert_equals(2, md_entry.number_of_orders.value)
                assert_equals(1, md_entry.aggressor_side.raw_value)
                assert_equals('Buy', md_entry.aggressor_side.value)
                assert_equals(0, md_entry.md_update_action.raw_value)
                assert_equals('New', md_entry.md_update_action.value)
                assert_equals('2', md_entry.md_entry_type.value)

            # We expect two trades in this message
            num_order_id_entries = 0
            for order_id_entry in message.no_order_id_entries:
                num_order_id_entries += 1
                if num_order_id_entries == 1:
                    assert_equals(644422848816, order_id_entry.order_id.value)
                    assert_equals(2, order_id_entry.last_qty.value)
                else:
                    assert_equals(644422848685, order_id_entry.order_id.value)
                    assert_equals(2, order_id_entry.last_qty.value)

        assert_equals(1, msg_count)


if __name__ == "__main__":
    nose.runmodule()


