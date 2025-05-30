#!/usr/bin/env python

import datetime
import unittest

import numpy as np
import numpy.testing as npt
import pytz

from data.utils import (
    datetime_to_timestamp,
    find_ge,
    find_le,
    get_data_vars_from_equation,
    roll_time,
    time_index_to_datetime,
    trunc,
)


class TestDataUtils(unittest.TestCase):
    def setUp(self):
        self.raw_timestamps = sorted(
            np.array(
                [
                    2144966400,
                    2145052800,
                    2145139200,
                    2145225600,
                    2145312000,
                    2145398400,
                    2145484800,
                ]
            )
        )

    def test_roll_time(self):
        self.assertEqual(roll_time(2, 2), 2)
        self.assertEqual(roll_time(4, 2), -1)
        self.assertEqual(roll_time(-1, 2), -1)
        self.assertEqual(roll_time(-5, 2), -1)

    def test_time_index_to_datetime(self):

        time_units = "seconds since 1950-01-01 00:00:00"

        res = time_index_to_datetime(self.raw_timestamps, time_units)
        self.assertEqual(len(res), 7)
        self.assertEqual(res[0], datetime.datetime(2017, 12, 21, 0, 0, tzinfo=pytz.UTC))

        raw_timestamp_not_list = 2144966400
        res_2 = time_index_to_datetime(raw_timestamp_not_list, time_units)

        self.assertEqual(
            res_2[0], datetime.datetime(2017, 12, 21, 0, 0, tzinfo=pytz.UTC)
        )

    def test_datetime_to_timestamp(self):
        time_units = "seconds since 1950-01-01 00:00:00"
        val = datetime.datetime(2017, 12, 21, 0, 0, tzinfo=pytz.UTC)

        res = datetime_to_timestamp(val, time_units)

        self.assertEqual(res, 2144966400)

    def test_find_le(self):

        self.assertEqual(2144966400, find_le(self.raw_timestamps, 2144966400))
        self.assertEqual(2144966400, find_le(self.raw_timestamps, 2145052700))
        self.assertEqual(2145484800, find_le(self.raw_timestamps, 2222222222))
        self.assertEqual(2144966400, find_le(self.raw_timestamps, 0))

    def test_find_ge(self):

        self.assertEqual(2144966400, find_ge(self.raw_timestamps, 2144966400))
        self.assertEqual(2145052800, find_ge(self.raw_timestamps, 2145052700))
        self.assertEqual(2145484800, find_ge(self.raw_timestamps, 2222222222))
        self.assertEqual(2144966400, find_ge(self.raw_timestamps, 0))

    def test_get_data_vars_from_equation(self):
        expected = sorted(["vosaline", "votemper"])

        result = sorted(
            get_data_vars_from_equation(
                "sspeed(depth, nav_lat, votemper - 273.15, vosaline)",
                ["vosaline", "votemper", "vozocrtx", "vomecrty"],
            )
        )

        self.assertEqual(expected, result)

    def test_trunc_truncates_one_value(self):
        expected = 3.14

        result = trunc(3.14444444444444444444, 2)

        npt.assert_allclose(result, expected, 0)

    def test_trunc_truncates_all_values(self):
        expected = np.array([3.141, 1.234])

        result = trunc(np.array([3.1414141414, 1.23456789]))

        npt.assert_allclose(result, expected)
