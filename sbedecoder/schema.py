import re
from lxml import etree
from sbedecoder.message import SBEMessage, TypeMessageField, EnumMessageField, SetMessageField, CompositeMessageField, \
    SBERepeatingGroupIterator


def convert_to_underscore(name):
    name = name.strip('@').strip('#')
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class SBESchema(object):
    def __init__(self):
        self.messages = []
        self.type_map = {}
        self.message_map = {}

        self.primitive_type_map = {
            'char': ('c', 1),
            'int': ('i', 4),
            'int8': ('b', 1),
            'int16': ('h', 2),
            'int32': ('i', 4),
            'int64': ('q', 8),
            'uint8': ('B', 1),
            'uint16': ('H', 2),
            'uint32': ('I', 4),
            'uint64': ('Q', 8),
        }

    @staticmethod
    def _build_type_definition(type_definition):
        type_configuration = dict((convert_to_underscore(x[0]), x[1]) for x in type_definition.items())
        type_configuration['type'] = type_definition.tag
        if type_definition.text:
            type_configuration['text'] = type_definition.text.strip()

        children_types = []
        for child in type_definition.getchildren():
            child_configuration = dict((convert_to_underscore(x[0]), x[1]) for x in child.items())
            child_configuration['type'] = child.tag
            if child.text:
                child_configuration['text'] = child.text.strip()
            children_types.append(child_configuration)
        type_configuration['children'] = children_types
        return type_configuration

    def _parse_types(self, xml_file, types_tag='types'):
        type_map = {}
        with open(xml_file) as input_schema_file:
            xml_context = etree.iterparse(input_schema_file, tag=types_tag)
            for action, elem in xml_context:
                # Now parse all the children under the types tag
                for type_def in elem.getchildren():
                    new_type = self._build_type_definition(type_def)
                    type_map[new_type['name']] = new_type
        return type_map

    @staticmethod
    def _parse_messages(xml_file, message_tag='message'):
        messages = []
        with open(xml_file) as input_schema_file:
            xml_context = etree.iterparse(input_schema_file)
            for action, elem in xml_context:
                local_name = etree.QName(elem.tag).localname
                if local_name == message_tag:
                    message_definition = dict((convert_to_underscore(x[0]), x[1]) for x in elem.items())
                    message_fields = []
                    message_groups = []
                    for child in elem.getchildren():
                        if child.tag == 'field':
                            message_field = dict((convert_to_underscore(x[0]), x[1]) for x in child.items())
                            message_fields.append(message_field)
                        elif child.tag == 'group':
                            message_group = dict((convert_to_underscore(x[0]), x[1]) for x in child.items())
                            group_fields = []
                            for group_child in child.getchildren():
                                group_field = dict((convert_to_underscore(x[0]), x[1]) for x in group_child.items())
                                group_fields.append(group_field)
                            message_group['fields'] = group_fields
                            message_groups.append(message_group)
                    message_definition['fields'] = message_fields
                    message_definition['groups'] = message_groups
                    messages.append(message_definition)
        return messages

    def _build_message_field(self, field_definition, offset, header_size=10, endian='<', add_header_size=True):
        field_name = convert_to_underscore(field_definition['name'])
        field_description = field_definition['description']
        field_type = self.type_map[field_definition['type']]
        field_type_type = field_type['type']
        field_semantic_type = field_type.get('semantic_type', None)
        is_string_type = (field_semantic_type == 'String')

        message_field = None
        if field_type_type == 'type':
            field_offset = offset
            if field_definition.get('offset', None) is not None:
                field_offset = int(field_definition.get('offset', None))
                if add_header_size:
                    field_offset += header_size

            primitive_type_fmt, primitive_type_size = self.primitive_type_map[field_type['primitive_type']]

            unpack_fmt = endian
            field_length = field_type.get('length', None)
            if field_length is not None:
                field_length = int(field_length)
                if is_string_type:
                    unpack_fmt += '%ss' % (str(field_length), )
                else:
                    unpack_fmt += '%s%s' % (str(field_length), primitive_type_fmt)
            else:
                # Field length is just the primitive type length
                field_length = primitive_type_size
                unpack_fmt += primitive_type_fmt

            constant = None
            optional = False
            if 'presence' in field_type:
                if field_type['presence'] == 'constant':
                    constant_prim_type = field_type['primitive_type']
                    if constant_prim_type == 'char':
                        constant = str(field_type['text'])
                    else:
                        constant = int(field_type['text'])
                elif field_type['presence'] == 'optional':
                    optional = True

            null_value = None
            if 'null_value' in field_type:
                null_value = long(field_type['null_value'])

            message_field = TypeMessageField(field_name, field_description,
                                             unpack_fmt, field_offset,
                                             field_length, null_value=null_value,
                                             constant=constant, optional=optional,
                                             is_string_type=is_string_type)
        elif field_type_type == 'enum':
            encoding_type = field_type['encoding_type']
            encoding_type_type = self.type_map[encoding_type]
            primitive_type_fmt, primitive_type_size = self.primitive_type_map[encoding_type_type['primitive_type']]

            field_offset = offset
            if field_definition.get('offset', None) is not None:
                field_offset = int(field_definition.get('offset', None))
                if add_header_size:
                    field_offset += header_size

            unpack_fmt = endian
            field_length = field_type.get('length', None)
            if field_length is not None:
                field_length = int(field_length)
                for i in xrange(field_length):
                    unpack_fmt += primitive_type_fmt
            else:
                # Field length is just the primitive type length
                field_length = primitive_type_size
                unpack_fmt += primitive_type_fmt

            enum_values = field_type['children']
            message_field = EnumMessageField(field_name, field_description, unpack_fmt,
                                             field_offset, enum_values, field_length)
        elif field_type_type == 'set':
            encoding_type = field_type['encoding_type']
            encoding_type_type = self.type_map[encoding_type]
            primitive_type_fmt, primitive_type_size = self.primitive_type_map[encoding_type_type['primitive_type']]

            field_offset = offset
            if field_definition.get('offset', None) is not None:
                field_offset = int(field_definition.get('offset', None))
                if add_header_size:
                    field_offset += header_size

            unpack_fmt = endian
            field_length = field_type.get('length', None)
            if field_length is not None:
                field_length = int(field_length)
                for i in xrange(field_length):
                    unpack_fmt += primitive_type_fmt
            else:
                # Field length is just the primitive type length
                field_length = primitive_type_size
                unpack_fmt += primitive_type_fmt

            choice_values = field_type['children']
            message_field = SetMessageField(field_name, field_description, unpack_fmt,
                                            field_offset, choice_values, field_length)
        elif field_type_type == 'composite':
            composite_parts = []

            field_offset = offset
            if field_definition.get('offset', None) is not None:
                field_offset = int(field_definition.get('offset', None))
                if add_header_size:
                    field_offset += header_size

            float_composite = False
            field_length = 0
            for child in field_type['children']:
                primitive_type_fmt, primitive_type_size = self.primitive_type_map[child['primitive_type']]
                unpack_fmt = endian + primitive_type_fmt

                constant = None
                optional = False
                if 'presence' in child:
                    if child['presence'] == 'constant':
                        constant_prim_type = child['primitive_type']
                        if constant_prim_type == 'char':
                            constant = str(child['text'])
                        else:
                            constant = int(child['text'])
                    elif child['presence'] == 'optional':
                        optional = True

                null_value = None
                if 'null_value' in child:
                    null_value = long(child['null_value'])

                # If a 'mantissa' field exists, assume we are working with a floating point value
                if child['name'] == 'mantissa':
                    float_composite = True

                composite_field = TypeMessageField(child['name'], child['description'],
                                                   unpack_fmt, field_offset, primitive_type_size,
                                                   null_value=null_value, constant=constant,
                                                   optional=optional)
                field_offset += primitive_type_size
                field_length += primitive_type_size
                composite_parts.append(composite_field)
 
            message_field = CompositeMessageField(field_name, field_description,
                                                  field_offset, field_length, composite_parts, 
                                                  float_value=float_composite)
        return message_field

    def get_message_type(self, template_id):
        return self.message_map.get(template_id, None)

    def parse(self, xml_file, message_tag="message", types_tag="types", endian='<'):
        self.type_map = self._parse_types(xml_file, types_tag=types_tag)
        self.messages = self._parse_messages(xml_file, message_tag=message_tag)

        # Now construct each message with its expected field types
        for message in self.messages:
            field_offset = 0
            # All messages start with a message size field
            message_template_id = int(message['id'])
            schema_block_length = int(message['block_length'])
            message_type = type(message['description'], (SBEMessage,), {'template_id': message_template_id,
                                                                        'schema_block_length': schema_block_length})

            message_fields = []
            # All messages start with a message size field
            message_size_field = TypeMessageField('message_size',
                                                  "Header Message Size",
                                                  '<H', field_offset, 2)
            field_offset += message_size_field.field_length
            message_fields.append(message_size_field)

            # Now grab the messageHeader type, it has to exist and populate the remaining header fields
            message_header_type = self.type_map['messageHeader']
            for header_field_type in message_header_type.get('children', []):
                primitive_type_fmt, primitive_type_size = self.primitive_type_map[header_field_type['primitive_type']]
                message_header_field = TypeMessageField(convert_to_underscore(header_field_type['name']),
                                                        'Header ' + header_field_type['name'],
                                                        primitive_type_fmt, field_offset, primitive_type_size)
                field_offset += message_header_field.field_length
                message_fields.append(message_header_field)

            setattr(message_type, 'header_size', field_offset)

            # Now run through the remaining types and update the fields
            for message_field_type in message.get('fields', []):
                message_field = self._build_message_field(message_field_type, field_offset)
                field_offset += message_field.field_length
                message_fields.append(message_field)

            # Assign all the fields to class type
            for message_field in message_fields:
                setattr(message_type, message_field.name, message_field)

            # Assign the fields array to keep around
            setattr(message_type, 'fields', message_fields)

            # Now figure out the message groups
            repeating_groups = []
            for group in message.get('groups', []):
                group_name = convert_to_underscore(group['name'])
                dimension_type = self.type_map[group['dimension_type']]
                # There are two fields we care about, block_length and num_in_group
                block_length_field = None
                num_in_group_field = None
                block_field_offset = 0
                for child in dimension_type['children']:
                    if child['name'] == 'blockLength':
                        primitive_type = child['primitive_type']
                        primitive_type_fmt, primitive_type_size = self.primitive_type_map[primitive_type]
                        block_length_field = TypeMessageField(convert_to_underscore(child['name']),
                                                              child['name'],
                                                              endian+primitive_type_fmt,
                                                              block_field_offset,
                                                              primitive_type_size)
                        block_field_offset += primitive_type_size
                    elif child['name'] == 'numInGroup':
                        primitive_type = child['primitive_type']
                        if 'offset' in child:
                            block_field_offset = int(child['offset'])
                        primitive_type_fmt, primitive_type_size = self.primitive_type_map[primitive_type]
                        num_in_group_field = TypeMessageField(convert_to_underscore(child['name']),
                                                              child['name'], endian+primitive_type_fmt,
                                                              block_field_offset, primitive_type_size)
                        block_field_offset += primitive_type_size

                group_field_offset = 0
                group_fields = []
                for group_field_def in group.get('fields', []):
                    group_field = self._build_message_field(group_field_def, group_field_offset, add_header_size=False)
                    group_field_offset += group_field.field_length
                    group_fields.append(group_field)

                repeating_group = SBERepeatingGroupIterator(group_name, block_length_field,
                                                            num_in_group_field, block_field_offset,
                                                            group_fields)
                repeating_groups.append(repeating_group)

            for repeating_group in repeating_groups:
                setattr(message_type, repeating_group.name, repeating_group)
            setattr(message_type, 'iterators', repeating_groups)

            self.message_map[message_template_id] = message_type
