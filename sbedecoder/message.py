from struct import unpack_from
import math


class SBEMessageField(object):
    def __init__(self):
        self.name = None
        self.original_name = None
        self.id = None
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

    def __str__(self, raw=False):
        if raw and self.value != self.raw_value:
            return "%s: %s (%s)" % (self.name, str(self.value), str(self.raw_value),)
        return "%s: %s" % (self.name, str(self.value),)


class TypeMessageField(SBEMessageField):
    def __init__(self, name=None, original_name=None,
                 id=None, description=None,
                 unpack_fmt=None, field_offset=None,
                 field_length=None, optional=False,
                 null_value=None, constant=None, is_string_type=False,
                 semantic_type=None, since_version=0):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.original_name = original_name
        self.id = id
        self.description = description
        self.unpack_fmt = unpack_fmt
        self.field_offset = field_offset
        self.field_length = field_length
        self.optional = optional
        self.null_value = null_value
        self.constant = constant
        self.is_string_type = is_string_type
        self.semantic_type = semantic_type
        self.since_version = since_version

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
    def __init__(self, name=None, original_name=None, id=None, description=None, unpack_fmt=None, field_offset=None,
                 choices=None, field_length=None, semantic_type=None, since_version=0):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.original_name = original_name
        self.id = id
        self.description = description
        self.unpack_fmt = unpack_fmt
        self.field_offset = field_offset
        self.choices = choices
        self.field_length = field_length
        self.text_to_name = dict((int(x['text']), x['name']) for x in choices)
        self.semantic_type = semantic_type
        self.since_version = since_version

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
    def __init__(self, name=None, original_name=None, id=None, description=None, unpack_fmt=None, field_offset=None,
                 enum_values=None, field_length=None, semantic_type=None, since_version=0):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.original_name = original_name
        self.id = id
        self.description = description
        self.unpack_fmt = unpack_fmt
        self.field_offset = field_offset
        self.enum_values = enum_values
        self.field_length = field_length
        self.text_to_enum_description = dict((x['text'], x.get('description', '')) for x in enum_values)
        self.text_to_enumerant = dict((x['text'], x['name']) for x in enum_values) # shorter repr of value
        self.semantic_type = semantic_type
        self.since_version = since_version

    @property
    def value(self):
        _raw_value = self.raw_value
        _value = self.text_to_enum_description.get(str(_raw_value), None)
        return _value

    @property
    def enumerant(self):
        _raw_value = self.raw_value
        _enumerant = self.text_to_enumerant.get(str(_raw_value), None)
        return _enumerant

    @property
    def raw_value(self):
        _raw_value = unpack_from(self.unpack_fmt, self.msg_buffer,
                                 self.msg_offset + self.relative_offset + self.field_offset)[0]
        return _raw_value


class CompositeMessageField(SBEMessageField):
    def __init__(self, name=None, original_name=None, id=None, description=None, field_offset=None, field_length=None,
                 parts=None, float_value=False, semantic_type=None, since_version=0):
        super(SBEMessageField, self).__init__()
        self.name = name
        self.original_name = original_name
        self.id = id
        self.description = description
        self.field_offset = field_offset
        self.field_length = field_length
        self.parts = parts
        self.float_value = float_value
        self.semantic_type = semantic_type
        self.since_version = since_version

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
    def __init__(self, msg_buffer, msg_offset, relative_offset, name, original_name, fields):
        self.msg_buffer = msg_buffer
        self.msg_offset = msg_offset
        self.relative_offset = relative_offset
        self.fields = fields
        self._groups = []
        self.name = name
        self.original_name = original_name

        for field in fields:
            setattr(self, field.name, field)

    def wrap(self):
        for field in self.fields:
            field.wrap(self.msg_buffer, self.msg_offset, relative_offset=self.relative_offset)

    def add_subgroup(self, subgroup):
        if not hasattr(self, subgroup.name):
            setattr(self, subgroup.name, [subgroup])
        else:
            getattr(self, subgroup.name).append(subgroup)
        self._groups.append(subgroup)

    @property
    def groups(self):
        for group in self._groups:
            group.wrap()
            yield group


class SBERepeatingGroupContainer(object):
    def __init__(self, name=None, original_name=None, id=None, block_length_field=None,
                 num_in_group_field=None, dimension_size=None, fields=None, groups=None,
                 since_version=0):
        self.msg_buffer = None
        self.msg_offset = 0
        self.group_start_offset = 0

        self.name = name
        self.original_name = original_name
        self.id = id
        self.block_length_field = block_length_field
        self.num_in_group_field = num_in_group_field

        if fields is None:
            self.fields = []
        else:
            self.fields = fields

        if groups is None:
            self.groups = []
        else:
            self.groups = groups
        self.since_version = since_version

        self.dimension_size = dimension_size
        self._repeating_groups = []

    def wrap(self, msg_buffer, msg_offset, group_start_offset):
        self.msg_buffer = msg_buffer
        self.msg_offset = msg_offset
        self.group_start_offset = group_start_offset
        self.block_length_field.wrap(msg_buffer, msg_offset, relative_offset=group_start_offset)
        self.num_in_group_field.wrap(msg_buffer, msg_offset, relative_offset=group_start_offset)
        block_length = self.block_length_field.value
        num_instances = self.num_in_group_field.value

        self._repeating_groups = []
        self.group_offset = group_start_offset + self.dimension_size

        # for each group, add the group length which can vary due to nested groups
        repeated_group_offset = group_start_offset + self.dimension_size
        nested_groups_length = 0
        for i in range(num_instances):
            repeated_group = SBERepeatingGroup(msg_buffer, msg_offset, repeated_group_offset + nested_groups_length, self.name, self.original_name, self.fields)
            self._repeating_groups.append(repeated_group)
            repeated_group_offset += block_length
            # now account for any nested groups
            for nested_group in self.groups:
                nested_groups_length += nested_group.wrap(
                    msg_buffer, msg_offset, repeated_group_offset + nested_groups_length)
                for nested_repeating_group in nested_group._repeating_groups:
                    repeated_group.add_subgroup(nested_repeating_group)

        size = self.dimension_size + (num_instances * block_length) + nested_groups_length
        return size

    @property
    def num_groups(self):
        return len(self._repeating_groups)

    @property
    def repeating_groups(self):
        for group in self._repeating_groups:
            group.wrap()
            yield group

    def __getitem__(self, index):
        group = self._repeating_groups[index]
        group.wrap()
        return group


class SBEMessage(object):
    def __init__(self):
        self.name = self.__class__.__name__
        self.msg_buffer = None
        self.msg_offset = None

    @staticmethod
    def parse_message(schema, msg_buffer, offset=0):
        """ Return a message by parsing a msg_buffer with the specified schema """
        template_id_offset = 2  # the 2 byte BlockHeader that starts all SBE Messages
        if schema.include_message_size_header:
            template_id_offset = 4  # Include a two byte message header (i.e for CME MDP)
        template_id = unpack_from('<H', msg_buffer, offset + template_id_offset)[0]
        message_type = schema.get_message_type(template_id)
        message = message_type()
        message.wrap(msg_buffer, offset)
        return message

    def wrap(self, msg_buffer, msg_offset):
        # Wrap the fields for decoding
        self.msg_buffer = msg_buffer
        self.msg_offset = msg_offset

        message_version = 0
        for field in self.fields:
            if message_version > 0 and field.since_version > message_version:
                continue
            field.wrap(msg_buffer, msg_offset)
            if field.name == 'version': # as we're iterating fields, save the version, which comes early as part of header
                message_version = field.value

        # Wrap the groups for decoding
        group_offset = self.schema_block_length + self.header_size
        for group in self.groups:
            if group.since_version <= message_version:
                group_offset += group.wrap(msg_buffer, msg_offset, group_offset)

    def __str__(self):
        return '%s' % (self.__class__.__name__,)


class SBEMessageFactory(object):
    def __init__(self, schema):
        self.schema = schema

    # This should return a tuple of (message, message_size)
    def build(self, msg_buffer, offset):
        raise NotImplementedError()


class MDPMessageFactory(SBEMessageFactory):
    def __init__(self, schema):
        super(MDPMessageFactory, self).__init__(schema)

    def build(self, msg_buffer, offset):
        # Peek at the template id to figure out what class to build
        # this looks past the starting 2 byte message_size header that is CME specific
        # and the 2 byte BlockHeader that starts all SBE Messages
        template_id = unpack_from('<H', msg_buffer, offset+4)[0]
        message_type = self.schema.get_message_type(template_id)
        message = message_type()
        message.wrap(msg_buffer, offset)
        return message, message.message_size.value
