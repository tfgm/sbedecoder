#!/usr/bin/env python
import six
import tempfile
import os

import nose
from six.moves import urllib
from nose.tools import assert_equals
from nose.tools import assert_is_instance
from nose.tools import assert_is_none

from mdp.secdef import SecDef


class TestSecDef:

    secdef_filename = None
    secdef_url = 'ftp://ftp.cmegroup.com/SBEFix/Production/secdef.dat.gz'
    secdef = None

    @classmethod
    def setup_class(cls):
        TestSecDef.secdef_filename = tempfile.NamedTemporaryFile().name
        urllib.request.urlretrieve(TestSecDef.secdef_url, TestSecDef.secdef_filename)
        TestSecDef.secdef = SecDef()
        TestSecDef.secdef.load(TestSecDef.secdef_filename)

    @classmethod
    def teardown_class(cls):
        os.remove(TestSecDef.secdef_filename)

    def test_lookup_security_id_not_found(self):
        print('Testing security lookup not found')
        assert_is_none(TestSecDef.secdef.lookup_security_id(9999999))

    def test_lookup_security_id_found(self):
        # just grab a key from the dict so we have something to lookup
        key_iter = six.iterkeys(TestSecDef.secdef.info)
        key = six.next(key_iter)
        value = TestSecDef.secdef.lookup_security_id(key)
        # should get back a tuple with two items
        assert_equals(len(value), 2)
        symbol, depth = value
        assert_is_instance(symbol, six.text_type)
        assert_is_instance(depth, six.integer_types)


if __name__ == '__main__':
    nose.runmodule()
