from __future__ import absolute_import

import os
import pytz
import datetime
import operator

from django.test import TestCase
from django.conf import settings
from django.utils import timezone

from zc_common import timezone as common_timezone


class TestTimezoneNow(TestCase):
    def test_getting_back_expected_timezone_by_default(self):
        # Test that we get back the default timezone we expect
        now = common_timezone.now()
        # Depending on the time of year, now.tzinfo changes for day light savings.
        self.assertEqual(now.tzinfo._tzinfos, pytz.timezone(settings.TIME_ZONE)._tzinfos)

    def test_passing_in_timezone(self):
        # Test that we can put in a custom timezone if needed
        now = common_timezone.now(tz=pytz.utc)
        self.assertEqual(now.tzinfo, pytz.utc)

    def test_equality_of_dates_and_times(self):
        # Test equality of the dates and times
        now = common_timezone.now().replace(tzinfo=None, microsecond=0)
        date_now = datetime.datetime.now().replace(microsecond=0)
        self.assertEqual(date_now, now)

    def test_conversion_works_as_expected(self):
        # Test that the conversion works as expected
        now = common_timezone.now(tz=pytz.utc).replace(tzinfo=None, microsecond=0)
        date_now = datetime.datetime.utcnow().replace(microsecond=0)
        self.assertEqual(date_now, now)


class TestTimezoneIsDaylightSavings(TestCase):
    def test_dst_time(self):
        dst_time = common_timezone.now().replace(month=7)
        self.assertTrue(common_timezone.is_daylight_savings_time(dst_time))

    def test_non_dst_time(self):
        non_dst_time = common_timezone.now().replace(month=12)
        self.assertFalse(common_timezone.is_daylight_savings_time(non_dst_time))


class TestTimezoneAdd(TestCase):
    def setUp(self):
        self.dst_time = common_timezone.datetime(2014, 7, 1)

    def test_not_crossing_dst(self):
        # Test not crossing daylight savings time
        delta = datetime.timedelta(days=7)
        expected = self.dst_time + delta
        outcome = common_timezone.math(self.dst_time, operator.add, delta)
        self.assertEqual(expected.replace(tzinfo=None), outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_daylight_savings_time(outcome))

    def test_crossing_dst_keep_hour(self):
        # Test crossing daylight savings time
        delta = datetime.timedelta(days=180)
        expected = self.dst_time + delta
        outcome = common_timezone.math(self.dst_time, operator.add, delta, keep_hour=True)
        self.assertEqual(expected.replace(tzinfo=None), outcome.replace(tzinfo=None))
        self.assertFalse(common_timezone.is_daylight_savings_time(outcome))

    def test_crossing_dst_default(self):
        # Test crossing daylight savings time, hour changes (default behaviour)
        delta = datetime.timedelta(days=180)
        expected = common_timezone.parse('12/27/2014 23:00')  # Would be 12/27/2014, but normalize subtracts an hour
        outcome = common_timezone.math(self.dst_time, operator.add, delta, keep_hour=False)
        self.assertEqual(expected.replace(tzinfo=None, hour=expected.hour), outcome.replace(tzinfo=None))
        self.assertFalse(common_timezone.is_daylight_savings_time(outcome))

    def test_crossing_dst_with_hour_delta(self):
        # Test crossing daylight savings time with delta that has an hour in it
        delta = datetime.timedelta(days=180, hours=2)
        expected = self.dst_time + delta
        outcome = common_timezone.math(self.dst_time, operator.add, delta, keep_hour=True)
        self.assertEqual(expected.replace(tzinfo=None), outcome.replace(tzinfo=None))
        self.assertFalse(common_timezone.is_daylight_savings_time(outcome))


class TestTimezoneSubtract(TestCase):
    def setUp(self):
        self.dst_time = common_timezone.datetime(2014, 7, 1)

    def test_not_crossing_dst(self):
        # Test not crossing daylight savings time
        delta = datetime.timedelta(days=7)
        expected = self.dst_time - delta
        outcome = common_timezone.math(self.dst_time, operator.sub, delta)
        self.assertEqual(expected.replace(tzinfo=None), outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_daylight_savings_time(outcome))

    def test_crossing_dst_keep_hour(self):
        # Test crossing daylight savings time
        delta = datetime.timedelta(days=180)
        expected = self.dst_time - delta
        outcome = common_timezone.math(self.dst_time, operator.sub, delta, keep_hour=True)
        self.assertEqual(expected.replace(tzinfo=None), outcome.replace(tzinfo=None))
        self.assertFalse(common_timezone.is_daylight_savings_time(outcome))

    def test_crossing_dst_default(self):
        # Test crossing daylight savings time, hour changes (default behaviour)
        delta = datetime.timedelta(days=180)
        expected = common_timezone.parse('1/1/2014 23:00')  # Would be 1/2/2014, but normalize subtracts an hour
        outcome = common_timezone.math(self.dst_time, operator.sub, delta, keep_hour=False)
        self.assertEqual(expected.replace(tzinfo=None, hour=expected.hour), outcome.replace(tzinfo=None))
        self.assertFalse(common_timezone.is_daylight_savings_time(outcome))

    def test_crossing_dst_with_hour_delta(self):
        # Test crossing daylight savings time with delta that has an hour in it
        delta = datetime.timedelta(days=180, hours=2)
        expected = self.dst_time - delta
        outcome = common_timezone.math(self.dst_time, operator.sub, delta, keep_hour=True)
        self.assertEqual(expected.replace(tzinfo=None), outcome.replace(tzinfo=None))
        self.assertFalse(common_timezone.is_daylight_savings_time(outcome))


class TestTimezoneCombine(TestCase):
    def test_default_behaviour(self):
        # Test default behaviour
        now = common_timezone.now()
        date = now.date()
        time = now.time()
        self.assertTrue(time.tzinfo is None)
        datetime_combined = datetime.datetime.combine(date, time)
        timezone_combined = common_timezone.combine(date, time)
        self.assertEqual(datetime_combined, timezone_combined.replace(tzinfo=None))
        self.assertEqual(timezone_combined.tzinfo, now.tzinfo)

    def test_passing_in_timezone(self):
        # Test passing in utc
        now = common_timezone.now(tz=pytz.utc)
        date = now.date()
        time = now.time()
        self.assertTrue(time.tzinfo is None)
        datetime_combined = datetime.datetime.combine(date, time)
        timezone_combined = common_timezone.combine(date, time, tz=pytz.utc)
        self.assertEqual(datetime_combined, timezone_combined.replace(tzinfo=None))
        self.assertEqual(timezone_combined.tzinfo, now.tzinfo)

    def test_time_having_tzinfo(self):
        # Test time having tzinfo
        now = common_timezone.now(tz=pytz.utc)
        date = now.date()
        time = now.time()
        self.assertTrue(time.tzinfo is None)
        time = time.replace(tzinfo=pytz.utc)  # Ensure that tzinfo is set
        datetime_combined = datetime.datetime.combine(date, time)  # Comes back aware
        timezone_combined = common_timezone.combine(date, time)
        self.assertEqual(datetime_combined, timezone_combined)
        self.assertEqual(timezone_combined.tzinfo, now.tzinfo)


class TestTimezoneParse(TestCase):
    def test_string_with_timezone(self):
        # Test returning with timezone information provided by the string
        expected = common_timezone.now()
        outcome = common_timezone.parse(str(expected))
        self.assertEqual(expected, outcome)

    def test_always_returning_aware_datetime(self):
        # Test always returning timezone information
        base = datetime.datetime(2014, 1, 1)
        expected = common_timezone.datetime(2014, 1, 1)
        outcome = common_timezone.parse(str(base))
        self.assertEqual(expected, outcome)

    def test_passing_kwargs(self):
        # Test passing kwargs
        expected = common_timezone.datetime(2014, 1, 1)
        date_string = "Jan 2014"
        default = datetime.datetime(2014, 1, 1)
        outcome = common_timezone.parse(date_string, default=default)
        self.assertEqual(expected, outcome)


class TestTimezoneDateTime(TestCase):
    def test_basic_construction(self):
        # Test default behaviour
        expected = datetime.datetime(2014, 1, 1)
        outcome = common_timezone.datetime(2014, 1, 1)
        self.assertEqual(expected, outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_aware(outcome))

    def test_passing_args_in_order(self):
        # Test passing args in order
        expected = datetime.datetime(2014, 1, 2, 3, 4, 5, 6)
        outcome = common_timezone.datetime(2014, 1, 2, 3, 4, 5, 6)
        self.assertEqual(expected, outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_aware(outcome))

    def test_passing_by_kwargs(self):
        # Test passing by kwargs
        expected = datetime.datetime(2014, 1, 2, 3, 4, microsecond=5, second=6)
        outcome = common_timezone.datetime(2014, 1, 2, 3, 4, microsecond=5, second=6)
        self.assertEqual(expected, outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_aware(outcome))

    def test_passing_with_tzinfo(self):
        # Test passing tzinfo
        expected = datetime.datetime(2013, 1, 2, tzinfo=pytz.utc)
        outcome = common_timezone.datetime(2013, 1, 2, tzinfo=pytz.utc)
        self.assertEqual(expected, outcome)


class TestTimezoneMisc(TestCase):
    """ Used for testing of misc functions that only require one or two tests """

    def test_datetime_min(self):
        expected = datetime.datetime.min
        outcome = common_timezone.datetime_min()
        self.assertEqual(expected, outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_aware(outcome))

    def test_datetime_max(self):
        expected = datetime.datetime.max
        outcome = common_timezone.datetime_max()
        self.assertEqual(expected, outcome.replace(tzinfo=None))
        self.assertTrue(common_timezone.is_aware(outcome))

    def test_get_timezone_name_in_dst(self):
        # Test getting timezone name in daylight savings time
        expected = 'PDT'
        outcome = common_timezone.get_timezone_name(common_timezone.datetime(2014, 7, 1))
        self.assertEqual(expected, outcome)

    def test_get_timezone_name_non_dst(self):
        # Test getting timezone name outside of daylight savings time
        expected = 'PST'
        outcome = common_timezone.get_timezone_name(common_timezone.datetime(2014, 1, 1))
        self.assertEqual(expected, outcome)

    def test_get_timezone_offset_in_dst(self):
        # Test getting the timezone offset in daylight savings time
        expected = '-0700'
        outcome = common_timezone.get_timezone_offset(common_timezone.datetime(2014, 7, 1))
        self.assertEqual(expected, outcome)

    def test_get_timezone_offset_non_dst(self):
        # Test getting the timezone offset outside of daylight savings time
        expected = '-0800'
        outcome = common_timezone.get_timezone_offset(common_timezone.datetime(2014, 1, 1))
        self.assertEqual(expected, outcome)

    def test_iso_javascript_format(self):
        expected = '2014-01-01T12:05:04Z'
        outcome = common_timezone.javascript_iso_format(
            common_timezone.datetime(2014, 1, 1, 12, 5, 4, tzinfo=pytz.utc)
        )
        self.assertEqual(expected, outcome)


class TestTimezoneActivate(TestCase):
    def setUp(self):
        common_timezone.deactivate()
        self.tz = pytz.timezone('Africa/Nairobi')

    def test_with_tzinfo_instance(self):
        common_timezone.activate(self.tz)
        self.assertEqual(self.tz, common_timezone.get_current_timezone())

    def test_only_takes_tzinfo_intance(self):
        with self.assertRaises(Exception):
            common_timezone.activate('Not a timezone')

    def test_it_extracts_get_timezone(self):
        class Obj(object):
            def get_timezone(self):
                return pytz.timezone('Africa/Nairobi')

        common_timezone.activate(Obj())
        self.assertEqual(self.tz, common_timezone.get_current_timezone())

    def tearDown(self):
        common_timezone.deactivate()


class TestTimezoneStartOfMonth(TestCase):
    def do_basic_tests(self, time, start_of_month):
        self.assertEqual(time.year, start_of_month.year)
        self.assertEqual(time.month, start_of_month.month)
        self.assertEqual(start_of_month.day, 1)
        self.assertEqual(start_of_month.hour, 0)
        self.assertEqual(start_of_month.second, 0)
        self.assertEqual(start_of_month.microsecond, 0)

    def test_normal_month(self):
        time = common_timezone.datetime(2014, 7, 5)
        start_of_month = common_timezone.to_start_of_month(time)
        self.do_basic_tests(time, start_of_month)
        self.assertEqual(
            common_timezone.get_timezone_offset(time), common_timezone.get_timezone_offset(start_of_month)
        )

    def test_dst_changing_month(self):
        time = common_timezone.datetime(2014, 11, 15)
        start_of_month = common_timezone.to_start_of_month(time)
        self.do_basic_tests(time, start_of_month)
        time_offset = common_timezone.get_timezone_offset(time)
        converted_offset = common_timezone.get_timezone_offset(start_of_month)
        self.assertEqual(time_offset, '-0800')
        self.assertEqual(converted_offset, '-0700')


class TestTimezoneEndOfMonth(TestCase):
    def do_basic_tests(self, time, end_of_month):
        last_day = common_timezone.get_last_day_of_month(time)
        self.assertEqual(time.year, end_of_month.year)
        self.assertEqual(time.month, end_of_month.month)
        self.assertEqual(end_of_month.day, last_day)
        self.assertEqual(end_of_month.hour, 23)
        self.assertEqual(end_of_month.second, 59)
        self.assertEqual(end_of_month.microsecond, 999999)

    def test_normal_month(self):
        time = common_timezone.datetime(2014, 7, 5)
        end_of_month = common_timezone.to_end_of_month(time)
        self.do_basic_tests(time, end_of_month)
        self.assertEqual(common_timezone.get_timezone_offset(time), common_timezone.get_timezone_offset(end_of_month))

    def test_dst_changing_month(self):
        time = common_timezone.datetime(2014, 11, 1)
        end_of_month = common_timezone.to_end_of_month(time)
        self.do_basic_tests(time, end_of_month)
        time_offset = common_timezone.get_timezone_offset(time)
        converted_offset = common_timezone.get_timezone_offset(end_of_month)
        self.assertEqual(time_offset, '-0700')
        self.assertEqual(converted_offset, '-0800')


class TestTimezoneLastDayOfMonth(TestCase):
    def test_normal_month(self):
        time = common_timezone.datetime(2014, 7, 5)
        last_day = common_timezone.get_last_day_of_month(time)
        self.assertEqual(last_day, 31)

    def test_non_leap_year(self):
        time = common_timezone.datetime(2014, 2, 3)
        last_day = common_timezone.get_last_day_of_month(time)
        self.assertEqual(last_day, 28)

    def test_leap_year(self):
        time = common_timezone.datetime(2000, 2, 3)
        last_day = common_timezone.get_last_day_of_month(time)
        self.assertEqual(last_day, 29)


class TestTimezoneToStartOfDay(TestCase):
    def test_to_start_of_day(self):
        time = common_timezone.now()
        start = common_timezone.to_start_of_day(time)
        self.assertEqual(time.year, start.year)
        self.assertEqual(time.month, start.month)
        self.assertEqual(time.day, start.day)
        self.assertEqual(time.tzinfo, start.tzinfo)
        self.assertEqual(start.hour, 0)
        self.assertEqual(start.minute, 0)
        self.assertEqual(start.second, 0)
        self.assertEqual(start.microsecond, 0)


class TestTimezoneToEndOfDay(TestCase):
    def test_to_end_of_day(self):
        time = common_timezone.now()
        start = common_timezone.to_end_of_day(time)
        self.assertEqual(time.year, start.year)
        self.assertEqual(time.month, start.month)
        self.assertEqual(time.day, start.day)
        self.assertEqual(time.tzinfo, start.tzinfo)
        self.assertEqual(start.hour, 23)
        self.assertEqual(start.minute, 59)
        self.assertEqual(start.second, 59)
        self.assertEqual(start.microsecond, 999999)


class TestTimezoneMonthlyIter(TestCase):
    def test_single_month(self):
        start = common_timezone.now()
        end = start
        count = 0
        for date in common_timezone.monthly_iter(start, end):
            self.assertEqual(date.month, start.month)
            self.assertEqual(date.year, start.year)
            count += 1
        self.assertEqual(count, 1)

    def test_multiple_months(self):
        start = common_timezone.datetime(2014, 11, 1)
        end = common_timezone.math(start, operator.add, datetime.timedelta(days=33))
        count = 0
        for date in common_timezone.monthly_iter(start, end):
            if count == 0:
                # On the first month
                self.assertEqual(date.month, start.month)
                self.assertEqual(date.month, start.month)
            else:
                # On the second month
                self.assertEqual(date.month, end.month)
                self.assertEqual(date.month, end.month)
            count += 1
        self.assertEqual(count, 2)

    def test_months_in_wrong_order(self):
        start = common_timezone.datetime(2014, 11, 1)
        end = common_timezone.math(start, operator.sub, datetime.timedelta(days=33))
        count = len(list(common_timezone.monthly_iter(start, end)))
        # No error is thrown, and no iteration happens
        self.assertEqual(count, 0)


class TestTimezoneIsHoliday(TestCase):
    def test_normal_day(self):
        time = timezone.datetime(2014, 7, 1)  # A tuesday
        is_business_day = common_timezone.is_business_day(time)
        self.assertTrue(is_business_day)

    def test_weekend(self):
        time = timezone.datetime(2014, 7, 26)  # A saturday
        is_business_day = common_timezone.is_business_day(time)
        self.assertFalse(is_business_day)

        is_business_day = common_timezone.is_business_day(time, include_weekends=False)
        self.assertTrue(is_business_day)

    def test_holiday(self):
        time = common_timezone.datetime(2014, 7, 4)  # July 4th
        is_business_day = common_timezone.is_business_day(time)
        self.assertFalse(is_business_day)


class TestTimezoneWeeklyIter(TestCase):
    def test_every_week_on_day(self):
        weeks = ['2014-07-04 00:00:00', '2014-07-11 00:00:00', '2014-07-18 00:00:00', '2014-07-25 00:00:00']
        i = 0
        friday = 5
        for date in common_timezone.weekly_iter(
            timezone.datetime(2014, 7, 1), timezone.datetime(2014, 7, 31), day=friday
        ):
            self.assertEqual(str(date), weeks[i])
            i += 1

    def test_every_week(self):
        weeks = [
            '2014-07-01 00:00:00', '2014-07-08 00:00:00', '2014-07-15 00:00:00', '2014-07-22 00:00:00',
            '2014-07-29 00:00:00'
        ]
        i = 0
        for date in common_timezone.weekly_iter(timezone.datetime(2014, 7, 1), timezone.datetime(2014, 7, 31)):
            self.assertEqual(str(date), weeks[i])
            i += 1

    def test_monday_with_friday_iter(self):
        weeks = ['2015-02-27 00:00:00']
        i = 0
        start = timezone.datetime(2015, 2, 23)
        end = start + datetime.timedelta(days=7)
        friday = 5
        for d in common_timezone.weekly_iter(start, end, day=5):
            self.assertEqual(str(d), weeks[i])
            i += 1

    def test_sunday_with_friday_iter(self):
        weeks = ['2015-02-27 00:00:00']
        i = 0
        start = timezone.datetime(2015, 2, 22)
        end = start + datetime.timedelta(days=7)
        friday = 5
        for d in common_timezone.weekly_iter(start, end, day=5):
            self.assertEqual(str(d), weeks[i])
            i += 1


class TestTimezoneToStartEndOfWeek(TestCase):
    def test_to_start_of_week(self):
        day = common_timezone.datetime(2014, 7, 1)
        sunday = common_timezone.to_start_of_week(day)
        self.assertEqual(sunday.isoweekday(), 1)

    def test_to_end_of_week(self):
        day = common_timezone.datetime(2014, 7, 1)
        saturday = common_timezone.to_end_of_week(day)
        self.assertEqual(saturday.isoweekday(), 7)
