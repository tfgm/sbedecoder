#!/usr/bin/env python

import binascii
import os
import tempfile

import pytest
from six.moves import urllib

from sbedecoder import MDPMessageFactory
from sbedecoder import SBEMessage
from sbedecoder import SBEParser
from sbedecoder import SBESchema

schema_url = 'ftp://ftp.cmegroup.com/SBEFix/Production/Templates/templates_FixBinary.xml'


@pytest.fixture(scope="module")
def mdp_schema():
    schema_filename = tempfile.NamedTemporaryFile().name
    urllib.request.urlretrieve(schema_url, schema_filename)
    urllib.request.urlcleanup()  # work around a bug in urllib under python 2.7 (https://stackoverflow.com/a/44734254)
    schema = SBESchema(include_message_size_header=True, use_description_as_message_name=True)
    try:
        from sbedecoder.generated import __messages__ as generated_messages
        schema.load(generated_messages)
    except:
        schema.parse(schema_filename)
    os.remove(schema_filename)
    return schema


@pytest.fixture(scope="module")
def mdp_parser(mdp_schema):
    msg_factory = MDPMessageFactory(mdp_schema)
    parser = SBEParser(msg_factory)
    return parser


def test_security_status_reset_statistics(mdp_parser):

    msg_buffer = binascii.a2b_hex('5603a9009c16d545349ad91428001e001e000100080003259845349ad914455300000000000000000000ffffff7fed4380150004')

    offset = 12

    recorded_messages = []
    for message in mdp_parser.parse(msg_buffer, offset):
        recorded_messages.append(message)

    # Validate that we parsed a security status message
    assert len(recorded_messages) == 1
    recorded_message = recorded_messages[0]
    assert recorded_message.template_id.value == 30
    assert recorded_message.name == 'SecurityStatus'
    assert recorded_message.trade_date.value == 17389
    assert recorded_message.transact_time.value == 1502401500001346819
    assert recorded_message.security_trading_event.value == 'Reset Statistics'
    assert recorded_message.security_trading_event.enumerant == 'ResetStatistics'
    assert recorded_message.security_trading_status.value == 'Pre Open'
    assert recorded_message.security_trading_status.enumerant == 'PreOpen'
    assert recorded_message.security_group.value == 'ES'
    assert recorded_message.asset.value == ''
    assert recorded_message.halt_reason.value == 'Group Schedule'
    assert recorded_message.halt_reason.enumerant == 'GroupSchedule'
    assert recorded_message.security_id.value is None


def test_security_status(mdp_parser):

    msg_buffer = binascii.a2b_hex('1409a900bbe7b5d5fe9ad91428001e001e000100080019989cd5fe9ad914455300000000000000000000ffffff7fed4380150001')
    offset = 12

    recorded_messages = []
    for message in mdp_parser.parse(msg_buffer, offset):
        recorded_messages.append(message)

    # Validate that we parsed a security status message
    assert len(recorded_messages) == 1
    recorded_message = recorded_messages[0]
    assert recorded_message.template_id.value == 30
    assert recorded_message.name == 'SecurityStatus'
    assert recorded_message.trade_date.value == 17389
    assert recorded_message.transact_time.value == 1502402370000951321
    assert recorded_message.match_event_indicator.value == 'EndOfEvent'
    assert recorded_message.security_trading_status.value == 'Pre Open'
    assert recorded_message.security_group.value == 'ES'
    assert recorded_message.asset.value == ''
    assert recorded_message.halt_reason.value == 'Group Schedule'
    assert recorded_message.security_id.value is None
    assert recorded_message.security_trading_event.value == 'No Cancel'


def test_incremental_refresh_verify_groups(mdp_parser):

    msg_buffer = binascii.a2b_hex(
        'c30fa90082dd3f8b069bd91478000b0020000100080095ab3d8b069bd914840000200002009bb1203602000002000000805d00003e2d140001000000010030000000000080e8ca113602000002000000805d00003f2d140001000000020130000000000018000000000000019c53980a9600000024131444010000000200000001010000')
    offset = 12

    msg_count = 0
    for message in mdp_parser.parse(msg_buffer, offset):
        msg_count += 1

        if msg_count == 1:
            assert message.template_id.value == 32
            assert message.transact_time.value == 1502402403112954773
            assert message.match_event_indicator.raw_value == 132
            assert message.match_event_indicator.value == 'LastQuoteMsg, EndOfEvent'

            groups = [x for x in message.groups]
            assert len(groups) == 2

            repeating_groups = groups[0].repeating_groups  # no_md_entries

            n = 0
            for repeating_group in repeating_groups:
                if n == 0:
                    assert repeating_group.md_entry_px.value == 243150.0
                    assert repeating_group.md_entry_size.value == 2
                    assert repeating_group.security_id.value == 23936
                    assert repeating_group.rpt_seq.value == 1322302
                    assert repeating_group.number_of_orders.value == 1
                    assert repeating_group.md_price_level.value == 1
                    assert repeating_group.md_update_action.raw_value == 0
                    assert repeating_group.md_update_action.value == 'New'
                    assert repeating_group.md_entry_type.raw_value == '0'
                    assert repeating_group.md_entry_type.value == 'Bid'
                elif n == 1:
                    assert repeating_group.md_entry_px.value == 243125.0
                    assert repeating_group.md_entry_size.value == 2
                    assert repeating_group.security_id.value == 23936
                    assert repeating_group.rpt_seq.value == 1322303
                    assert repeating_group.number_of_orders.value == 1
                    assert repeating_group.md_price_level.value == 2
                    assert repeating_group.md_update_action.raw_value == 1
                    assert repeating_group.md_update_action.value == 'Change'
                    assert repeating_group.md_entry_type.raw_value == '0'
                    assert repeating_group.md_entry_type.value == 'Bid'
                n += 1
            assert n == 2

            repeating_groups = groups[1].repeating_groups  # no_order_id_entries

            n = 0
            for repeating_group in repeating_groups:
                if n == 0:
                    assert repeating_group.order_id.value == 644422849436
                    assert repeating_group.md_order_priority.value == 5437133604
                    assert repeating_group.md_display_qty.value == 2
                    assert repeating_group.reference_id.value == 1
                    assert repeating_group.order_update_action.value == 'Update'
                    assert repeating_group.order_update_action.raw_value == 1
                n += 1
            assert n == 1


def test_incremental_refresh_verify_group_attributes(mdp_parser):

    msg_buffer = binascii.a2b_hex(
        'c30fa90082dd3f8b069bd91478000b0020000100080095ab3d8b069bd914840000200002009bb1203602000002000000805d00003e2d140001000000010030000000000080e8ca113602000002000000805d00003f2d140001000000020130000000000018000000000000019c53980a9600000024131444010000000200000001010000')
    offset = 12

    msg_count = 0
    for message in mdp_parser.parse(msg_buffer, offset):
        msg_count += 1

        if msg_count == 1:
            assert message.template_id.value == 32
            assert message.transact_time.value == 1502402403112954773
            assert message.match_event_indicator.raw_value == 132
            assert message.match_event_indicator.value == 'LastQuoteMsg, EndOfEvent'

            n = 0
            for repeating_group in message.no_md_entries:
                if n == 0:
                    assert repeating_group.md_entry_px.value == 243150.0
                    assert repeating_group.md_entry_size.value == 2
                    assert repeating_group.security_id.value == 23936
                    assert repeating_group.rpt_seq.value == 1322302
                    assert repeating_group.number_of_orders.value == 1
                    assert repeating_group.md_price_level.value == 1
                    assert repeating_group.md_update_action.raw_value == 0
                    assert repeating_group.md_update_action.value == 'New'
                    assert repeating_group.md_entry_type.raw_value == '0'
                    assert repeating_group.md_entry_type.value == 'Bid'
                elif n == 1:
                    assert repeating_group.md_entry_px.value == 243125.0
                    assert repeating_group.md_entry_size.value == 2
                    assert repeating_group.security_id.value == 23936
                    assert repeating_group.rpt_seq.value == 1322303
                    assert repeating_group.number_of_orders.value == 1
                    assert repeating_group.md_price_level.value == 2
                    assert repeating_group.md_update_action.raw_value == 1
                    assert repeating_group.md_update_action.value == 'Change'
                    assert repeating_group.md_entry_type.raw_value == '0'
                    assert repeating_group.md_entry_type.value == 'Bid'
                n += 1
            assert n == 2

            n = 0
            for repeating_group in message.no_order_id_entries:
                if n == 0:
                    assert repeating_group.order_id.value == 644422849436
                    assert repeating_group.md_order_priority.value == 5437133604
                    assert repeating_group.md_display_qty.value == 2
                    assert repeating_group.reference_id.value == 1
                    assert repeating_group.order_update_action.value == 'Update'
                    assert repeating_group.order_update_action.raw_value == 1
                n += 1
            assert n == 1


def test_incremental_refresh_multiple_messages(mdp_parser):

    msg_buffer = binascii.a2b_hex('c90fa9008a15428b069bd91458000b00200001000800e7c43d8b069bd91484000020000180b2654d360200008e0000000a610000f62fac003000000007013000000000001800000000000001e44c980a960000002b13144401000000010000000101000058000b002000010008006f203f8b069bd9148400002000018017336b3602000004000000805d0000402d140002000000020131000000000018000000000000016153980a960000002c131444010000000200000001010000')
    offset = 12

    msg_count = 0
    for message in mdp_parser.parse(msg_buffer, offset):
        if msg_count == 0:
            assert message.name == 'MDIncrementalRefreshBook'
            n = 0
            for entry in message.no_md_entries:
                if n == 0:
                    assert entry.md_entry_px.value == 243225.0
                    assert entry.md_entry_size.value == 142
                n += 1
            assert n == 1
        elif msg_count == 1:
            assert message.name == 'MDIncrementalRefreshBook'
            n = 0
            for entry in message.no_md_entries:
                if n == 0:
                    assert entry.md_entry_px.value == 243275.0
                assert entry.md_entry_size.value == 4
                n += 1
            assert n == 1
        msg_count += 1
    assert msg_count == 2


def test_incremental_refresh_trade_summary(mdp_parser):

    msg_buffer = binascii.a2b_hex('2f0aa9007decc6d2059bd91460000b002a000100080085b89fd2059bd91401000020000100f981d336020000020000000a610000fe2aac00020000000100ffffffff000010000000000000023051980a960000000200000000000000ad50980a960000000200000000000000')
    offset = 12

    msg_count = 0
    for message in mdp_parser.parse(msg_buffer, offset):
        msg_count += 1
        assert message.template_id.value == 42
        assert message.transact_time.value == 1502402400015595653
        assert message.match_event_indicator.raw_value == 1
        assert message.match_event_indicator.value == 'LastTradeMsg'

        # This message has two repeating groups
        assert len(message.groups) == 2

        # We expect only 1 md entry
        for md_entry in message.no_md_entries:
            assert md_entry.md_entry_px.value == 243450.0
            assert md_entry.md_entry_size.value == 2
            assert md_entry.security_id.value == 24842
            assert md_entry.rpt_seq.value == 11283198
            assert md_entry.number_of_orders.value == 2
            assert md_entry.aggressor_side.raw_value == 1
            assert md_entry.aggressor_side.value == 'Buy'
            assert md_entry.md_update_action.raw_value == 0
            assert md_entry.md_update_action.value == 'New'
            assert md_entry.md_entry_type.value == '2'

        # We expect two trades in this message
        num_order_id_entries = 0
        for order_id_entry in message.no_order_id_entries:
            num_order_id_entries += 1
            if num_order_id_entries == 1:
                assert order_id_entry.order_id.value == 644422848816
                assert order_id_entry.last_qty.value == 2
            else:
                assert order_id_entry.order_id.value == 644422848685
                assert order_id_entry.last_qty.value == 2

    assert msg_count == 1


def test_sbemessage_parse_message(mdp_schema):

    msg_buffer = binascii.a2b_hex('5603a9009c16d545349ad91428001e001e000100080003259845349ad914455300000000000000000000ffffff7fed4380150004')

    offset = 12

    recorded_message = SBEMessage.parse_message(mdp_schema, msg_buffer, offset)

    # Validate that we parsed a security status message
    assert recorded_message.template_id.value == 30
    assert recorded_message.name == 'SecurityStatus'
    assert recorded_message.trade_date.value == 17389
    assert recorded_message.transact_time.value == 1502401500001346819
    assert recorded_message.security_trading_event.value == 'Reset Statistics'
    assert recorded_message.security_trading_event.enumerant == 'ResetStatistics'
    assert recorded_message.security_trading_status.value == 'Pre Open'
    assert recorded_message.security_trading_status.enumerant == 'PreOpen'
    assert recorded_message.security_group.value == 'ES'
    assert recorded_message.asset.value == ''
    assert recorded_message.halt_reason.value == 'Group Schedule'
    assert recorded_message.halt_reason.enumerant == 'GroupSchedule'
    assert recorded_message.security_id.value is None
