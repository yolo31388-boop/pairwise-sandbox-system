"""Pytest bootstrap: give plain test classes unittest.TestCase assertions.

The test classes in tests/ call self.assertIsNotNone but do not inherit
from unittest.TestCase. Test files must not be modified, so the
assertion methods are injected here at collection time.
"""

import unittest


def pytest_pycollect_makeitem(collector, name, obj):
    if (
        isinstance(obj, type)
        and name.startswith("Test")
        and not issubclass(obj, unittest.TestCase)
    ):
        for attr in dir(unittest.TestCase):
            if attr.startswith(("assert", "fail")) and not hasattr(obj, attr):
                setattr(obj, attr, getattr(unittest.TestCase, attr))
        obj.failureException = AssertionError
