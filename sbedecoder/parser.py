class SBEParser(object):
    def __init__(self, msg_factory):
        self.factory = msg_factory

    def parse(self, message_buffer, offset=0):
        msg_offset = offset
        while msg_offset < len(message_buffer):
            message = self.factory.build(message_buffer, msg_offset)
            msg_offset += message.message_size.value
            yield message
