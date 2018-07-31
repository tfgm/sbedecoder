[![Build Status](https://travis-ci.org/tfgm/sbedecoder.svg?branch=master)](https://travis-ci.org/tfgm/sbedecoder)

Python based Simple Binary Encoding (SBE) decoder
=================================================

Overview
--------

sbedecoder is a simple python package for parsing SBE encoded data.  

sbedecoder dynamically generates an SBE parser from an xml description of the format. This is accomplished by
creating an instance of `SBESchema()` and calling it's `parse()` method with a file name:

    from sbedecoder import SBESchema
    schema = SBESchema()
    schema.parse('path/to/schema.xml')

The `SBESchema()` can be initialized with `include_message_size_header=True` if the messages being parsed
require an extra 2 byte (unit16) framing message_size_header field (i.e. for CME MDP 3.0).

By default, message names are derived from the "name" field of the message definition in the schema.
In some cases (i.e. CME MDP 3.0), the message "description" field of the message definition provides a
more friendly name for the message. To use message descriptions as the name of the message,
initialize your SBESchema with `use_description_as_message_name=True`.

For convenience, an `MDPSchema()` subclass of `SBESchema()` is provided with `include_message_size_header=True`
and `use_description_as_message_name=True` specifically to handle CME Group MDP 3.0 schema's.

Messages are parsed from any structure that looks like a buffer containing the raw binary
data (buffer, str, bytearay, etc).  To parse SBE encoded data into a message based on a
schema instance, just call `SBEMessage.parse_message()`:

    from sbedecoder import SBEMessage
    message = SBEMessage.parse_message(schema, msg_buffer, offset=0)

`offset` is an optional parameter that indicates where within the msg_buffer the message
starts (including the size header if the schema has `include_message_size_header` set).

A parsed message is represented as an instance of the `SBEMessage()` class.  `SBEMessages()` are
comprised of zero or more `sbedecoder.message.SBEField()` instances and zero or more
`sbedecoder.message.SBERepeatingGroup()` instances. An `SBEField()` object can be one of a primitive
`TypeMessageField()`, a `SetMessageField()` or an `EnumMessageField()`

**Note:** Unless using code generation, you cannot store the messages for later processing.
You must process the messages on each iteration, because the messages re-use instances of
field objects, wrapping them around new values.

The CME Group sends MDP 3.0 messages in packets that include a 4 byte sequence number
and a 8 byte timestamp.  In addition, there can be multiple messages in a single packet
and each message is framed the with a 2 byte (unit16) message size field as mentioned above.

To parse these messages, you can create a `MDPSchema()`, use that to create a
`MDPMessageFactory()` and then create a `SBEParser()` which can then iterate over the messages in
a packet like this:

    from sbedecoder import MDPSchema
    from sbedecoder import MDPMessageFactory
    from sbedecoder import SBEParser

    schema = SBESchema()
    schema.parse('path/to/schema.xml')
    message_factory = MDPMessageFactory(schema)
    message_parser = SBEParser(message_factory)

    for packet in SOME_DATASOURCE:
       for message in message_parser.parse(packet, offset=12):
           process(message)


This "Message Factory" concept could easily be extended to new framing schemes by creating a new sub class of `SBEMessageFactory()`

For more information on SBE, see: http://www.fixtradingcommunity.org/pg/structure/tech-specs/simple-binary-encoding.

Install
-------

The sbedecoder project is available on PyPI:

    pip install sbedecoder
    
If you are installing from source:

    python setup.py install

**Note**: The SBE decoder has only been tested with python 2.7 and 3.6.  On Windows, we typically use the 
Anaconda python distribution.  Anaconda does not distribute python's test code.  If you have 
issues with dpkt (ImportError: No module named test), you can either install the latest dpkt 
from source (https://github.com/kbandla/dpkt) or just comment out the import (from test import 
pystone) in ..\\Anaconda\\lib\\site-packages\\dpkt\\decorators.py.  Newer versions of dpkt no 
longer have this dependency.


mdp_decoder.py
--------------

mdp_decoder.py serves as an example of using the sbedecoder package.  It is a full decoder for processing CME Group
MDP 3.0 (MDP3) messages from a pcap file.  For help with using mdp_decoder.py:
 
    mdp_decoder.py --help

An SBE template for CME Group MDP 3.0 market data can be found at 
ftp://ftp.cmegroup.com/SBEFix/Production/Templates/templates_FixBinary.xml

Example output:

    :packet - timestamp: 2015-06-25 09:45:01.924492 sequence_number: 93696727 sending_time: 1435243501924423666 
    ::MDIncrementalRefreshVolume -  transact_time: 1435243501923350056 match_event_indicator: LastVolumeMsg (2)
    :::no_md_entries - num_groups: 1
    ::::md_entry_size: 4483 security_id: 559884 rpt_seq: 2666379 md_update_action: New (0) md_entry_type: e 
    ::MDIncrementalRefreshBook -  transact_time: 1435243501923350056 match_event_indicator: LastQuoteMsg (4)
    :::no_md_entries - num_groups: 2
    ::::md_entry_px: 18792.0 ({'mantissa': 187920000000, 'exponent': -7}) md_entry_size: 1 security_id: 559884 rpt_seq: 2666380 number_of_orders: 1 md_price_level: 1 md_update_action: Delete (2) md_entry_type: Bid (0) 
    ::::md_entry_px: 18746.0 ({'mantissa': 187460000000, 'exponent': -7}) md_entry_size: 6 security_id: 559884 rpt_seq: 2666381 number_of_orders: 1 md_price_level: 10 md_update_action: New (0) md_entry_type: Bid (0) 

Example output (with `--pretty`):


```
packet - timestamp: 2016-03-10 15:33:21.301819 sequence_number: 76643046 sending_time: 1454679022595400091
    Message 1 of 2: TID 32 (MDIncrementalRefreshBook) v6
        TransactTime (60): 02/05/2016 07:30:22.595256135 (1454679022595256135)
        MatchEventIndicator (5799): LastQuoteMsg
        NoMDEntries (268): 1
        Entry 1
            MDEntryPx (270): 98890000000 (9889.0)
            MDEntrySize (271): 296
            SecurityID (48): 807004
            RptSeq (83): 14273794
            NumberOfOrders (346): 16
            MDPriceLevel (1023): 2
            MDUpdateAction (279): Change
            MDEntryType (269): Offer
    Message 2 of 2: TID 32 (MDIncrementalRefreshBook) v6
        TransactTime (60): 02/05/2016 07:30:22.595256135 (1454679022595256135)
        MatchEventIndicator (5799): LastImpliedMsg, EndOfEvent
        NoMDEntries (268): 8
        Entry 1
            MDEntryPx (270): 475000000 (47.5)
            MDEntrySize (271): 296
            SecurityID (48): 817777
            RptSeq (83): 1573080
            NumberOfOrders (346): Null
            MDPriceLevel (1023): 2
            MDUpdateAction (279): Change
            MDEntryType (269): ImpliedBid
        Entry 2...
```

mdp_book_builder.py
-------------------

mdp_book_builder.py serves as an example of using the sbedecoder package to build limit orderbooks for a given contract.

For help with using mdp_book_builder.py:

    mdp_book_builder.py --help

Versioning
----------

sbedecoder supports the `sinceVersion` attribute of fields, enumerants, groups, ..., etc, and so it can
decode older (e.g. archived) binary data so long as the schema has evolved correctly to maintain support
for the old format

Performance
-----------

sbedecoder itself isn't optimized for performance however it can be adequate for simple backtesting scenarios amd 
post trade analytics.  Due to the amount of printing done by mdp_decoder.py, it can be quite slow to parse large 
pcap files.

PyPy
----

For improved performance (4 to 5x), sbedecoder will run under PyPy.  Assuming your pypy install is in /opt:

    /opt/pypy/bin/pip install lxml
    /opt/pypy/bin/pip install dpkt
    /opt/pypy/bin/pypy setup.py install
    
Code Generation
---------------

A SBE class generator script is available to generate a python file that contains the class definitions that match those
that are created dynamically via the SBESchema.parse method.

For help with using sbe_class_generator.py:

    sbe_class_generator.py --help

An usage would be (from the generator directory):

/sbe_class_generator.py --schema schema.xml --output generated.py --template ./sbe_message.tmpl

This command will output a file called generated.py containing the class definitions that were dynamically created
while parsing the 'schema.xml' file. The template file used to generated the classes is contained in sbe_message.tmpl.

The generated.py file can simply be used for examining the class construction, or it can replace the contents of the
generated.py file in the sbedecoder core project. By replacing the generated.py file in the sbedecoder package, a
developer will get access to the class definitions in the IDE.

In order to make use of the standard parser functionality using the generated code one should use the SBESchema.load
method instead of the parse method.

An example of how to do this is below and is contained in the mdp_book_builder.py script:

    try:
        from sbedecoder.generated import __messages__ as generated_messages
        mdp_schema.load(generated_messages)
    except:
        mdp_schema.parse(args.schema)

