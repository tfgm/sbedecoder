import re
import gzip


class SecDef(object):
    def __init__(self):
        self.info = {}

    def load(self, secdef_filename):
        tag_regexp = re.compile('(?:^|\x01)(48|55)=(.*?)(?=\x01)')
        depth_regexp = re.compile('1022=GBX\x01264=(\d+)')
        with gzip.open(secdef_filename, 'rb') as f:
            for line in f:
                matches = tag_regexp.findall(line)
                if matches:
                    tag = dict(matches)
                    security_id = int(tag['48'])
                    symbol = tag['55']
                    # now we need the depth
                    m = depth_regexp.search(line)
                    depth = int(m.group(1))
                    self.info[security_id] = (symbol, depth)

    def lookup_security_id(self, security_id):
        if security_id in self.info:
            return self.info[security_id]
        return None

