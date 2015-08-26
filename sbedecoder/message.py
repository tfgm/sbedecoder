from struct import unpack_from
import math


class SBEMessageField(object):
    def __init__(self):
        self.name = None
        self.description = None
        self.msg_buffer = None
        self.msg_offset = None
        self.unpack_fmt = None
        self.field_offset = 0
        self.relative_offset = 0

    def wrap(self, msg_buffer, base_offset, relative_offset=0):
        self.msg_buffer = msg_buffer
        self.msg_offset = base_offset
        self.relative_offset = relative_offset

    @property
    def value(self):
        return None

    @property
    def raw_value(self):
        return None

    def __str__(self):
        if self.value != self.raw_value:
            return "%s: %s (%s)" % (self.name, str(self.value), str(self.raw_value),)
        return "%s: %s" % (self.name, str(self.value),)


class TypeMessageField(SBEMessageField):
    def __init__(self, name=None, description=None,
                 unpack_fmt=None, field_offset=None,
                 field_length=None, optional=False,
                 null_value=None, constant=None, is_string_type=False):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.description = description
        self.unpack_fmt = unpack_fmt
        self.field_offset = field_offset
        self.field_length = field_length
        self.optional = optional
        self.null_value = null_value
        self.constant = constant
        self.is_string_type = is_string_type

    @property
    def value(self):
        _raw_value = self.raw_value

        # If this is a null value, return None
        if self.null_value:
            if _raw_value == self.null_value:
                return None

        # If this is a string type, strip any null characters
        if self.is_string_type:
            parts = _raw_value.split('\0', 1)
            return parts[0]

        return _raw_value

    @property
    def raw_value(self):
        if self.constant is not None:
            return self.constant

        _raw_value = unpack_from(self.unpack_fmt, self.msg_buffer,
                                 self.msg_offset + self.relative_offset + self.field_offset)[0]

        return _raw_value


class SetMessageField(SBEMessageField):
    def __init__(self, name=None, description=None, unpack_fmt=None, field_offset=None,
                 choices=None, field_length=None):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.description = description
        self.unpack_fmt = unpack_fmt
        self.field_offset = field_offset
        self.choices = choices
        self.field_length = field_length
        self.text_to_name = dict((int(x['text']), x['name']) for x in choices)

    @property
    def value(self):
        _raw_value = self.raw_value
        _value = ''
        _num_values = 0
        for i in xrange(self.field_length*8):
            bit_set = 1 & (_raw_value >> i)
            if bit_set:
                if _num_values > 0:
                    _value += ', '
                _value += self.text_to_name[i]
                _num_values += 1
        return _value

    @property
    def raw_value(self):
        _raw_value = unpack_from(self.unpack_fmt, self.msg_buffer,
                                 self.msg_offset + self.relative_offset + self.field_offset)[0]
        return _raw_value


class EnumMessageField(SBEMessageField):
    def __init__(self, name=None, description=None, unpack_fmt=None, field_offset=None,
                 enum_values=None, field_length=None):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.description = description
        self.unpack_fmt = unpack_fmt
        self.field_offset = field_offset
        self.enum_values = enum_values
        self.field_length = field_length
        self.text_to_enum_value = dict((x['text'], x['description']) for x in enum_values)

    @property
    def value(self):
        _raw_value = self.raw_value
        _value = self.text_to_enum_value.get(str(_raw_value), None)
        return _value

    @property
    def raw_value(self):
        _raw_value = unpack_from(self.unpack_fmt, self.msg_buffer,
                                 self.msg_offset + self.relative_offset + self.field_offset)[0]
        return _raw_value


class CompositeMessageField(SBEMessageField):
    def __init__(self, name=None, description=None, field_offset=None, field_length=None,
                 parts=None, float_value=False):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.description = description
        self.field_offset = field_offset
        self.field_length = field_length
        self.parts = parts
        self.float_value = float_value

        # Map the parts
        for part in self.parts:
            setattr(self, part.name, part)

    def wrap(self, msg_buffer, msg_offset, relative_offset=0):
        self.msg_buffer = msg_buffer
        self.msg_offset = msg_offset
        self.relative_offset = relative_offset

        for part in self.parts:
            part.wrap(msg_buffer, msg_offset, relative_offset=relative_offset)

    @property
    def value(self):
        _raw_value = self.raw_value

        if self.float_value:
            # We expect two fields, mantissa and exponent as part of this field
            mantissa = _raw_value.get('mantissa', None)
            exponent = _raw_value.get('exponent', None)
            if mantissa is None or exponent is None:
                return None 
            return float(mantissa) * math.pow(10, exponent)

        return self.raw_value

    @property
    def raw_value(self):
        part_dict = dict((p.name, p.value) for p in self.parts)
        return part_dict


class SBERepeatingGroup:
    def __init__(self, fields):
        self.fields = fields

        for field in fields:
            setattr(self, field.name, field)

    def wrap(self, msg_buffer, msg_offset, group_start_offset):
        for field in self.fields:
            field.wrap(msg_buffer, msg_offset, relative_offset=group_start_offset)


class SBERepeatingGroupIterator(object):
    def __init__(self, name=None, block_length_field=None, num_in_group_field=None, dimension_size=None, group_fields=None):
        self.msg_buffer = None
        self.msg_offset = 0
        self.group_start_offset = 0

        self.name = name
        self.block_length_field = block_length_field
        self.num_in_group_field = num_in_group_field
        self.block_length = 0
        self.num_groups = 0
        self.num_groups_read = 0
        self.group_start_offset = 0
        self.group_fields = group_fields
        self.dimension_size = dimension_size

    def wrap(self, msg_buffer, msg_offset, group_start_offset):
        self.msg_buffer = msg_buffer
        self.msg_offset = msg_offset
        self.group_start_offset = group_start_offset

        self.block_length_field.wrap(msg_buffer, msg_offset, relative_offset=group_start_offset)
        self.num_in_group_field.wrap(msg_buffer, msg_offset, relative_offset=group_start_offset)
        self.block_length = self.block_length_field.value
        self.num_groups = self.num_in_group_field.value
        return self.dimension_size + self.block_length * self.num_groups

    def __iter__(self):
        self.num_groups_read = 0
        return self

    def __len__(self):
        return self.num_groups

    def next(self):
        if self.num_groups_read < self.num_groups:
            group_offset = self.group_start_offset + self.block_length * self.num_groups_read + self.dimension_size
            group = SBERepeatingGroup(self.group_fields)
            group.wrap(self.msg_buffer, self.msg_offset, group_offset)
            self.num_groups_read += 1
            return group
        else:
            raise StopIteration


class SBEMessage(object):
    def __init__(self):
        self.name = self.__class__.__name__
        self.msg_buffer = None
        self.msg_offset = None

    def wrap(self, msg_buffer, msg_offset):
        # Wrap the fields for decoding
        self.msg_buffer = msg_buffer
        self.msg_offset = msg_offset

        for field in self.fields:
            field.wrap(msg_buffer, msg_offset)

        # Wrap the groups for decoding
        group_offset = self.schema_block_length + self.header_size
        for group_iterator in self.iterators:
            group_offset += group_iterator.wrap(msg_buffer, msg_offset, group_offset)

    def __str__(self):
        return '%s' % (self.__class__.__name__,)


class SBEMessageFactory(object):
    def __init__(self, schema):
        self.schema = schema

    def build(self, msg_buffer, offset):
        # Peek at the template id to figure out what class to build
        template_id = unpack_from('<H', msg_buffer, offset+4)[0]
        message_type = self.schema.get_message_type(template_id)
        message = message_type()
        message.wrap(msg_buffer, offset)
        return message
