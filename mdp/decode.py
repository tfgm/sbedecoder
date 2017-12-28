from struct import unpack_from
from datetime import datetime
import binascii
from . import prettyprinter

def handle_repeating_groups(group_container, msg_version, indent, skip_fields, secdef):
    for group in group_container.groups:
        if group.since_version > msg_version:
            continue
        print(':::{} - num_groups: {}'.format(group.name, group.num_groups))
        for group_field in group.repeating_groups:
            group_fields = ''
            for group_field in group_field.fields:
                if group_field.since_version > msg_version:
                    continue
                if secdef and group_field.id == '48':
                    security_id = group_field.value
                    symbol_info = secdef.lookup_security_id(security_id)
                    if symbol_info:
                        symbol = symbol_info[0]
                        group_fields += 'security_id: {} [{}]'.format(security_id, symbol) + ' '
                        continue
                group_fields += str(group_field) + ' '
            print('::::{}'.format(group_fields))
        handle_repeating_groups(group, msg_version, indent + ':', skip_fields=skip_fields, secdef=secdef)


def decode_packet(mdp_parser, timestamp, data, skip_fields, print_data, pretty, secdef):
    if print_data:
        print('data: {}'.format(binascii.b2a_hex(data)))

    # parse the packet header: http://www.cmegroup.com/confluence/display/EPICSANDBOX/MDP+3.0+-+Binary+Packet+Header
    sequence_number = unpack_from("<i", data, offset=0)[0]
    sending_time = unpack_from("<Q", data, offset=4)[0]

    print(':packet - timestamp: {} sequence_number: {} sending_time: {} '.format(
        timestamp, sequence_number, sending_time))

    if pretty:
        # Two-passes on the parse so we can count the messages and print e.g. "Message 3 of 5"
        #
        # Cannot store messages from the iteration, as field objects get reused and overwritten
        # on each round.
        n = len(list(mdp_parser.parse(data, offset=12)))  # pass 1 to count the msgs in iterable

        for i, mdp_message in enumerate(mdp_parser.parse(data, offset=12)):  # pass 2 to actually print
            prettyprinter.pretty_print(mdp_message, i, n, secdef)
    else:
        for mdp_message in mdp_parser.parse(data, offset=12):
            message_fields = ''
            for field in mdp_message.fields:
                if field.since_version > mdp_message.version.value:  # field is later version than msg
                    continue
                if field.name not in skip_fields:
                    message_fields += ' ' + str(field)
            print('::{} - {}'.format(mdp_message, message_fields))
            handle_repeating_groups(mdp_message, mdp_message.version.value, indent='::::', skip_fields=skip_fields, secdef=secdef)

