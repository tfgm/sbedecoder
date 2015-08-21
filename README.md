Python based Simple Binary Encoding (SBE) decoder
=================================================

Overview
--------

sbedecoder is a simple python package for parsing SBE encoded data.  

sbedecoder dynamically generates a SBE parser from an xml description of the format. This is accomplished by
creating an instance of SBESchema() and calling it's parse() method with a file name:

    from sbedecoder import SBESchema
    schema = SBESchema()
    schema.parse('path/to/schema.xml')

A message parser based on this schema is created by first creating an instance of a SBEMessageFactory()
and then creating an instance of SBEParser() using the SBEMessageFactory():

    from sbedecoder import SBEMessageFactory
    from sbedecoder import SBEParser
    
    message_factory = SBEMessageFactory(schema)
    message_parser = SBEParser(message_factory)

Messages are parsed from any structure that looks like a buffer containing the raw binary 
data (buffer, str, bytearay, etc): 

    for message in mdp_parser.parse(data, offset=offset):
        process(message)

A parsed message is represented as an instance of
the SBEMessage() class.  SBEMessages are comprised of zero or more sbedecoder.message.SBEField() instances and 
zero or more sbedecoder.message.SBERepeatingGroup() instances. An SBEField() object can be one of a primitive 
TypeMessageField(), a SetMessageField() or an EnumMessageField()

For more information on SBE, see: http://www.fixtradingcommunity.org/pg/structure/tech-specs/simple-binary-encoding.

Install
-------

    python setup.py install

mdp_decoder.py
--------------

mdp_decoder.py serves as an example of using the sbedecoder package.  It is a full decoder for processing CME Group
MDP 3.0 (MDP3) messages from a pcap file.  For help with using mdp_decoder.py:
 
    mdp_decoder.py --help

An SBE template for CME Group MDP 3.0 market data can be found at 
ftp://ftp.cmegroup.com/SBEFix/Production/Templates/templates_FixBinary.xml

Example, output:

    :packet - timestamp: 2015-06-25 09:45:01.924492 sequence_number: 93696727 sending_time: 1435243501924423666 
    ::MDIncrementalRefreshVolume -  transact_time: 1435243501923350056 match_event_indicator: LastVolumeMsg (2)
    :::no_md_entries - num_groups: 1
    ::::md_entry_size: 4483 security_id: 559884 rpt_seq: 2666379 md_update_action: New (0) md_entry_type: e 
    ::MDIncrementalRefreshBook -  transact_time: 1435243501923350056 match_event_indicator: LastQuoteMsg (4)
    :::no_md_entries - num_groups: 2
    ::::md_entry_px: 18792.0 ({'mantissa': 187920000000, 'exponent': -7}) md_entry_size: 1 security_id: 559884 rpt_seq: 2666380 number_of_orders: 1 md_price_level: 1 md_update_action: Delete (2) md_entry_type: Bid (0) 
    ::::md_entry_px: 18746.0 ({'mantissa': 187460000000, 'exponent': -7}) md_entry_size: 6 security_id: 559884 rpt_seq: 2666381 number_of_orders: 1 md_price_level: 10 md_update_action: New (0) md_entry_type: Bid (0) 

mdp_book_builder.py
--------------

mdp_book_builder.py serves as an example of using the sbedecoder package to build limit orderbooks for a given contract.

For help with using mdp_book_builder.py:

    mdp_book_builder.py --help

Performance
----------

sbedecoder itself isn't optimized for performance however it can be adequate for simple backtesting scenarios amd 
post trade analytics.  Due to the amount of printing done by mdp_decoder.py, it can be quite slow to parse large 
pcap files.

PyPy
----

For improved performance (4 to 5x), sbedecoder will run under PyPy.  Assuming your pypy install is in /opt:

    /opt/pypy/bin/pip install lxml
    /opt/pypy/bin/pip install dpkt
    /opt/pypy/bin/pypy setup.py install
    
