#!/usr/bin/env python

"""

Generate a python file containing the message definitions contained in the provided XML schema.

This generated file can then be used to replace the current dynamic file generation that is
done in the base sbedecoder.

"""

import os
import sys
import subprocess
from datetime import datetime
from mako.template import Template
from sbedecoder import SBESchema
from argparse import ArgumentParser


class Bunch:
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(v, dict):
                v = Bunch(v)
            if isinstance(v, list):
                v = [Bunch(temp) for temp in v]
            self.__dict__[k] = v

    def __str__(self):
        return ', '.join("{!s}={!r}".format(k, v) for (k, v) in self.__dict__.items())


def process_command_line():
    arg_parser = ArgumentParser(
        description="Generate a python file containing the message definitions for a given schema file.",
        version="0.1")

    arg_parser.add_argument("--schema", default='templates_FixBinary.xml',
        help="Name of the SBE schema xml file (default: %(default)s)")

    arg_parser.add_argument("--output", default='generated.py',
        help="Name of the generated output file (default: %(default)s)")

    arg_parser.add_argument("--template", default='sbe_message.tmpl',
        help="Name of template file to use for generating the class output (default: %(default)s)")

    arg_parser.add_argument("--include-message-size-header", action='store_true',
        help="pass include_message_size_header=True to SBESchema", default=False)

    arg_parser.add_argument("--use-description-as-message-name", action='store_true',
        help="pass use_description_as_message_name=True to SBESchema", default=False)

    args = arg_parser.parse_args()

    # check number of arguments, verify values, etc.:
    if not os.path.isfile(args.schema):
        arg_parser.error("sbe schema xml file '{}' not found".format(args.schema))

    if not os.path.isfile(args.template):
        arg_parser.error("class template file '{}' not found".format(args.template))

    return args


def build_field_description(field):
    field_description = {'name': field.name, 'type': type(field).__name__, 'kwargs': field.__dict__}

    if field_description['type'] == 'SetMessageField':
        if 'text_to_name' in field_description['kwargs']:
            field_description['kwargs'].pop('text_to_name')

    if field_description['type'] == 'EnumMessageField':
        if 'text_to_enum_value' in field_description['kwargs']:
            field_description['kwargs'].pop('text_to_enum_value')

    if field_description['type'] == 'CompositeMessageField':
        if 'exponent' in field_description['kwargs']:
            field_description['kwargs'].pop('exponent')

        if 'mantissa' in field_description['kwargs']:
            field_description['kwargs'].pop('mantissa')

        converted_parts = []
        for part in field_description['kwargs']['parts']:
            part_def = {'type': type(part).__name__, 'kwargs': part.__dict__}
            converted_parts.append(part_def)
        field_description['kwargs']['parts'] = converted_parts
    return field_description


def main(argv=None):
    cmd_line_args = process_command_line()
    schema_file = cmd_line_args.schema
    output_file = cmd_line_args.output
    template_file_path = cmd_line_args.template

    use_msg_size_header = cmd_line_args.include_message_size_header
    use_desc_as_name = cmd_line_args.use_description_as_message_name
    mdp_schema = SBESchema(include_message_size_header=use_msg_size_header, use_description_as_message_name=use_desc_as_name)
    mdp_schema.parse(schema_file)

    # Translate the message classes into a description that can be converted into a field description
    message_descriptions = []
    for template_id, message_class in mdp_schema.message_map.items():
        message_description = {'name': message_class.__name__,
                               'base_classes': ','.join([x.__name__ for x in message_class.__bases__]),
                               'attributes': {},
                               'fields': [],
                               'groups': []}
        message_attributes = message_description['attributes']
        message_fields = message_description['fields']
        message_groups = message_description['groups']

        # Update the common attributes for each of these messages
        message_attributes['message_id'] = message_class.message_id
        message_attributes['schema_block_length'] = message_class.schema_block_length
        message_attributes['header_size'] = message_class.header_size

        # Update the fields
        for field in message_class.fields:
            field_description = build_field_description(field)
            message_fields.append(field_description)

        # Update the groups
        for repeating_group in message_class.groups:
            group_description = {'name': repeating_group.name,
                                'original_name': repeating_group.original_name,
                                'id': repeating_group.id,
                                'type': type(repeating_group).__name__,
                                'dimension_size': repeating_group.dimension_size,
                                'since_version': repeating_group.since_version}

            block_length_field = repeating_group.block_length_field
            group_description['block_length_field'] = {'name': block_length_field.name,
                                                      'original_name': block_length_field.original_name,
                                                      'type': type(block_length_field).__name__,
                                                      'kwargs': block_length_field.__dict__}

            num_in_group_field = repeating_group.num_in_group_field
            group_description['num_in_group_field'] = {'name': num_in_group_field.name,
                                                      'original_name': num_in_group_field.original_name,
                                                      'type': type(num_in_group_field).__name__,
                                                      'kwargs': num_in_group_field.__dict__}

            group_fields = []
            for field in repeating_group.fields:
                field_description = build_field_description(field)
                group_fields.append(field_description)
            group_description['fields'] = group_fields
            message_groups.append(group_description)

        message_descriptions.append(message_description)

    template = Template(filename=template_file_path)
    generation_date = datetime.now()
    docstring = ''' Generated SBE Message Classes '''

    messages = dict((x['name'], Bunch(x)) for x in message_descriptions)
    field_types = {}
    for key, value in mdp_schema.type_map.items():
        field_types[key] = Bunch(value)

    with open(output_file, 'w') as outfile:
        outfile.writelines(template.render(generation_date=generation_date,
                                           docstring=docstring,
                                           messages=messages))

    # PEP 8 the output file
    subprocess.check_output(["autopep8", "--in-place", "--aggressive", output_file])

    return 0


if __name__ == '__main__':
    status = main()
    sys.exit(status)
