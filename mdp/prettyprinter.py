
from datetime import datetime

def mdp3time(t):
    dt = datetime.fromtimestamp(t // 1000000000)
    s = dt.strftime('%m/%d/%Y %H:%M:%S')
    s += '.' + str(int(t % 1000000000)).zfill(9)
    return s

def adjustField(field, secdef):
    if field.semantic_type == 'UTCTimestamp':
        return '{} ({})'.format(mdp3time(field.value), field.value)

    # Add the symbol from the secdef file if we can
    if secdef and field.id == '48':
        security_id = field.value
        symbol_info = secdef.lookup_security_id(security_id)
        if symbol_info:
            symbol = symbol_info[0]
            return '{} [{}]'.format(security_id, symbol)

    # Use enum name rather than description, to match MC
    if hasattr(field, 'enumerant'):
        value = field.enumerant
    else:
        value = field.value

    # Make prices match MC (no decimal)
    if field.semantic_type == 'Price':
        if value is not None:
            value = '{} ({})'.format(int(float(value) * 10000000), value)

    value = '<Empty>' if value == '' else value
    value = 'Null' if value is None else value
    return value


def pretty_print(msg, i, n, secdef):
    print '    Message %d of %d: TID %d (%s) v%d' % (i + 1, n, msg.template_id.value, msg.name, msg.version.value)
    for field in [x for x in msg.fields if x.original_name[0].isupper()]:
        if field.since_version > msg.version.value: # field is later version than msg
            continue
        value = adjustField(field, secdef)
        if field.id:
            print '        %s (%s): %s' % (field.original_name, field.id, value)
        else:
            print '        %s: %s' % (field.original_name, value)
    for group_container in msg.groups:
        if group_container.since_version > msg.version.value:
            continue
        print '        %s (%d): %d' % (
        group_container.original_name, group_container.id, group_container.num_groups)
        for i_instance, group_instance in enumerate(group_container):
            print '        Entry %d' % (i_instance + 1)
            for field in group_instance.fields:
                if field.since_version > msg.version.value:
                    continue
                value = adjustField(field, secdef)
                print '            %s (%s): %s' % (field.original_name, field.id, value)

