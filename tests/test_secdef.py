#!/usr/bin/env python
import os
import tempfile

import six
from six.moves import urllib
import pytest

from mdp.secdef import SecDef

secdef_url = 'ftp://ftp.cmegroup.com/SBEFix/Production/secdef.dat.gz'


@pytest.fixture()
def secdef():
    secdef_filename = tempfile.NamedTemporaryFile().name
    urllib.request.urlretrieve(secdef_url, secdef_filename)
    urllib.request.urlcleanup()  # work around a bug in urllib under python 2.7 (https://stackoverflow.com/a/44734254)
    secdef = SecDef()
    secdef.load(secdef_filename)
    os.remove(secdef_filename)
    return secdef  # provide the fixture value


def test_lookup_security_id_not_found(secdef):
    print('Testing security lookup not found')
    assert secdef.lookup_security_id(9999999) is None


def test_lookup_security_id_found(secdef):
    # just grab a key from the dict so we have something to lookup
    key_iter = six.iterkeys(secdef.info)
    key = six.next(key_iter)
    value = secdef.lookup_security_id(key)
    # should get back a tuple with two items
    assert len(value) == 2
    symbol, depth = value
    assert isinstance(symbol, six.text_type)
    assert isinstance(depth, six.integer_types)
