import re
from lxml import etree
from sbedecoder.message import SBEMessage, TypeMessageField, EnumMessageField, SetMessageField, CompositeMessageField, \
    SBERepeatingGroupContainer


def convert_to_underscore(name):
    name = name.strip('@').strip('#')
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class SBESchema(object):
    def __init__(self, include_message_size_header=False, use_description_as_message_name=False):
        self.messages = []
        self.include_message_size_header = include_message_size_header
        self.use_description_as_message_name = use_description_as_message_name
        self.initial_types = {
           "char": {"children": [], "description": "char", "name": "char", "primitive_type": "char", "type": "type"},
           "int": {"children": [], "description": "int", "name": "int", "primitive_type": "int32", "type": "type"},
           "int8": {"children": [], "description": "int8", "name": "int8", "primitive_type": "int8", "type": "type"},
           "int16": {"children": [], "description": "int16", "name": "int16", "primitive_type": "int16", "type": "type"},
           "int32": {"children": [], "description": "int32", "name": "int32", "primitive_type": "int32", "type": "type"},
           "int64": {"children": [], "description": "int64", "name": "int64", "primitive_type": "int64", "type": "type"},
           "uint8": {"children": [], "description": "uint8", "name": "uint8", "primitive_type": "uint8", "type": "type"},
           "uint16": {"children": [], "description": "uint16", "name": "uint16", "primitive_type": "uint16", "type": "type"},
           "uint32": {"children": [], "description": "uint32", "name": "uint32", "primitive_type": "uint32", "type": "type"},
           "uint64": {"children": [], "description": "uint64", "name": "uint64", "primitive_type": "uint64", "type": "type"},
           "float": {"children": [], "description": "float", "name": "float", "primitive_type": "float", "type": "type"},
           "double": {"children": [], "description": "double", "name": "double", "primitive_type": "double", "type": "type"}
        }
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
            'float': ('f', 4),
            'double': ('d', 8),
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
        type_map = self.initial_types
        with open(xml_file) as input_schema_file:
            xml_context = etree.iterparse(input_schema_file, tag=types_tag, remove_comments=True)
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
                    SBESchema._parse_message_elements(elem, message_definition)
                    messages.append(message_definition)
        return messages

    @staticmethod
    def _parse_message_elements(elements, definition):
        fields = []
        groups = []
        for child in elements.getchildren():
            if child.tag == 'field':
                field = dict((convert_to_underscore(x[0]), x[1]) for x in child.items())
                field['converted_name'] = convert_to_underscore(field['name'])
                fields.append(field)
            elif child.tag == 'group':
                group = dict((convert_to_underscore(x[0]), x[1]) for x in child.items())
                SBESchema._parse_message_elements(child, group)
                group['converted_name'] = convert_to_underscore(group['name'])
                groups.append(group)
        definition['fields'] = fields
        definition['groups'] = groups

    def _build_message_field(self, field_definition, offset, header_size=10, endian='<', add_header_size=True):
        field_original_name = field_definition['name']
        field_name = convert_to_underscore(field_original_name)
        field_id = field_definition['id']
        field_description = field_definition.get('description', '')
        field_type = self.type_map[field_definition['type']]
        field_type_type = field_type['type']
        field_semantic_type = field_definition.get('semantic_type', None)
        field_since_version = int(field_definition.get('since_version','0'))

        message_field = None
        if field_type_type == 'type':
            is_string_type = field_type['primitive_type'] == 'char' and 'length' in field_type and int(
                field_type['length']) > 1
            field_offset = offset
            if field_definition.get('offset', None) is not None:
                field_offset = int(field_definition.get('offset', None))
                if add_header_size:
                    field_offset += header_size

            primitive_type_fmt, primitive_type_size = self.primitive_type_map[field_type['primitive_type']]

            field_length = field_type.get('length', None)
            if field_length is not None:
                field_length = int(field_length)
                if is_string_type:
                    unpack_fmt = '%ds' % field_length # unpack as string (which may be null-terminated if shorter)
                else:
                    unpack_fmt = '%s%s%s' % (endian, str(field_length), primitive_type_fmt)
            else:
                # Field length is just the primitive type length
                field_length = primitive_type_size
                unpack_fmt = '%s%s' % (endian, primitive_type_fmt)

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

            message_field = TypeMessageField(name=field_name, original_name=field_original_name,
                                             id=field_id, description=field_description,
                                             unpack_fmt=unpack_fmt, field_offset=field_offset,
                                             field_length=field_length, null_value=null_value,
                                             constant=constant, optional=optional,
                                             is_string_type=is_string_type,
                                             semantic_type=field_semantic_type,
                                             since_version=field_since_version)
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
            message_field = EnumMessageField(name=field_name,
                                             original_name=field_original_name,
                                             id=field_id,
                                             description=field_description,
                                             unpack_fmt=unpack_fmt,
                                             field_offset=field_offset,
                                             enum_values=enum_values,
                                             field_length=field_length,
                                             semantic_type=field_semantic_type,
                                             since_version=field_since_version)
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
            message_field = SetMessageField(name=field_name, original_name=field_original_name,
                                            id=field_id, description=field_description, unpack_fmt=unpack_fmt,
                                            field_offset=field_offset, choices=choice_values, field_length=field_length,
                                            semantic_type=field_semantic_type, since_version=field_since_version)
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
                child_since_version = int(child.get('since_version', '0'))

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

                composite_field = TypeMessageField(name=child['name'], original_name=child['name'],
                                                   description=child.get('description', ''),
                                                   unpack_fmt=unpack_fmt, field_offset=field_offset,
                                                   field_length=primitive_type_size,
                                                   null_value=null_value, constant=constant,
                                                   optional=optional, semantic_type=field_semantic_type,
                                                   since_version=child_since_version)
                field_offset += primitive_type_size
                field_length += primitive_type_size
                composite_parts.append(composite_field)

            message_field = CompositeMessageField(name=field_name, original_name=field_original_name,
                                                  id=field_id, description=field_description,
                                                  field_offset=field_offset, field_length=field_length,
                                                  parts=composite_parts,
                                                  float_value=float_composite, semantic_type=field_semantic_type,
                                                  since_version=field_since_version)
        return message_field

    def get_message_type(self, template_id):
        return self.message_map.get(template_id, None)

    def _determine_field_length(self, field):
        field_type = field.get('primitive_type', field['type'])
        if field_type in self.primitive_type_map:
            return self.primitive_type_map[field_type][1] #second value is byte size
        else:
            field_def = self.type_map[field['type']]
            if 'encoding_type' in field_def and field_def['encoding_type'] in self.primitive_type_map:
                return self.primitive_type_map[field_def['encoding_type']][1]

            #otherwise it's a regular composite field
            block_length = 0
            for child_field in field_def['children']:
                block_length += self._determine_field_length(child_field)
            return block_length

    def _determine_block_length(self, message):
        if 'block_length' in message:
            return int(message['block_length'])

        # block length was not defined but we should be able to calculate it by adding
        # length of types up until we hit the first var field or repeating group
        block_length = 0
        for field in message['fields']:
            block_length += self._determine_field_length(field)

        return block_length

    def _construct_header(self, message):
        field_offset = 0
        # All messages start with a message size field
        message_id = int(message['id'])
        schema_block_length = self._determine_block_length(message)
        type_name = message['description'] if self.use_description_as_message_name else message['name']
        message_type = type(type_name, (SBEMessage,), {'message_id': message_id,
                            'schema_block_length': schema_block_length})
        self.message_map[message_id] = message_type
        setattr(message_type, 'fields', [])

        # If messages start with a message size field
        if self.include_message_size_header:
            message_size_field = TypeMessageField(name='message_size', original_name='message_size',
                                                  description="Header Message Size",
                                                  unpack_fmt='<H', field_offset=field_offset, field_length=2)
            field_offset += message_size_field.field_length
            message_type.fields.append(message_size_field)
            setattr(message_type, 'message_size', message_size_field)

        # Now grab the messageHeader type, it has to exist and populate the remaining header fields
        message_header_type = self.type_map['messageHeader']
        for header_field_type in message_header_type.get('children', []):
            primitive_type_fmt, primitive_type_size = self.primitive_type_map[header_field_type['primitive_type']]
            message_header_field = TypeMessageField(name=convert_to_underscore(header_field_type['name']),
                                                    original_name=header_field_type['name'],
                                                    description='Header ' + header_field_type['name'],
                                                    unpack_fmt=primitive_type_fmt,
                                                    field_offset=field_offset,
                                                    field_length=primitive_type_size)
            field_offset += message_header_field.field_length
            message_type.fields.append(message_header_field)
            setattr(message_type, message_header_field.name, message_header_field)
        setattr(message_type, 'header_size', field_offset)
        return field_offset

    def _add_fields(self, field_offset, entity, entity_type, endian, add_header_size=True):
        # Now run through the remaining types and update the fields
        for field_type in entity.get('fields', []):
            field = self._build_message_field(field_type, field_offset, endian=endian, add_header_size=add_header_size)
            field_offset += field.field_length
            entity_type.fields.append(field)
            # make it an attribute too
            setattr(entity_type, field.name, field)

    def _add_groups(self, entity, entity_type, endian):
        # Now figure out the message groups
        repeating_groups = []
        for group_type in entity.get('groups', []):
            group_name = convert_to_underscore(group_type['name'])
            group_original_name = group_type['name']
            group_since_version = int(group_type.get('since_version','0'))
            dimension_type = self.type_map[group_type['dimension_type']]
            # There are two fields we care about, block_length and num_in_group
            block_length_field = None
            num_in_group_field = None
            block_field_offset = 0
            for child in dimension_type['children']:
                if child['name'] == 'blockLength':
                    primitive_type = child['primitive_type']
                    primitive_type_fmt, primitive_type_size = self.primitive_type_map[primitive_type]
                    block_length_field = TypeMessageField(name=convert_to_underscore(child['name']),
                                                          original_name=child['name'],
                                                          description=child['name'],
                                                          unpack_fmt=endian + primitive_type_fmt,
                                                          field_offset=block_field_offset,
                                                          field_length=primitive_type_size,
                                                          semantic_type=child.get('semantic_type'))
                    block_field_offset += primitive_type_size
                elif child['name'] == 'numInGroup':
                    primitive_type = child['primitive_type']
                    if 'offset' in child:
                        block_field_offset = int(child['offset'])
                    primitive_type_fmt, primitive_type_size = self.primitive_type_map[primitive_type]
                    num_in_group_field = TypeMessageField(name=convert_to_underscore(child['name']),
                                                          original_name=child['name'],
                                                          description=child['name'],
                                                          unpack_fmt=endian + primitive_type_fmt,
                                                          field_offset=block_field_offset,
                                                          field_length=primitive_type_size,
                                                          semantic_type=child.get('semantic_type'))
                    block_field_offset += primitive_type_size

            group_field_offset = 0
            repeating_group = SBERepeatingGroupContainer(name=group_name, original_name=group_original_name,
                                                         id=int(group_type['id']),
                                                         block_length_field=block_length_field,
                                                         num_in_group_field=num_in_group_field,
                                                         dimension_size=block_field_offset,
                                                         since_version=group_since_version)

            self._add_fields(group_field_offset, group_type, repeating_group, endian, add_header_size=False)

            repeating_groups.append(repeating_group)
            setattr(entity_type, repeating_group.name, repeating_group)

            # handle nested groups
            self._add_groups(group_type, repeating_group, endian)

        setattr(entity_type, 'groups', repeating_groups)

    def _construct_body(self, message, field_offset, endian):
        message_id = int(message['id'])
        message_type = self.get_message_type(message_id)
        self._add_fields(field_offset, message, message_type, endian, add_header_size=True)
        self._add_groups(message, message_type, endian)

    def parse(self, xml_file, message_tag="message", types_tag="types", endian='<'):
        self.type_map = self._parse_types(xml_file, types_tag=types_tag)
        self.messages = self._parse_messages(xml_file, message_tag=message_tag)

        # Now construct each message with its expected field types
        for message in self.messages:
            field_offset = self._construct_header(message)
            self._construct_body(message, field_offset, endian)

    def load(self, messages):
        self.messages = messages
        self.message_map = dict((m.message_id, m) for m in messages)


class MDPSchema(SBESchema):
    def __init__(self):
        super(MDPSchema, self).__init__(include_message_size_header=True, use_description_as_message_name=True)
