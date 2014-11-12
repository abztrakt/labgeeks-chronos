""" Begin testing for Chronos, import proper libraries and models.
"""
from django.test import TestCase
from datetime import datetime
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from labgeeks_chronos import models as c_models
from labgeeks_chronos import views as c_views
from labgeeks_chronos import utils as c_utils
import unittest


class StartTestCase(TestCase):
    """ Create models for the test cases. Make sure all test cases inherit from
    this class so that they have models. Feel free to add or edit models.
    """
    def setUp(self):

        # Create users and set permissions
        self.ryu = User.objects.create(username='Ryu', password='hadouken', email='ryu@streetfighter.com')
        self.ken = User.objects.create(username='Ken', password='shoryuken', email='ken@streetfighter.com')
        self.akuma = User.objects.create(username='Akuma', password='shun goku satsu', email='akuma@streetfighter.com')

        # Ryu can do anything an admin can do.
        self.ryu.is_active = True
        self.ryu.is_staff = True
        self.ryu.is_superuser = True

        # Ken can do anything a regular staff can do, minus things a superuser
        # can do.
        self.ken.is_active = True
        self.ken.is_staff = True
        self.ken.is_superuser = False

        # Akuma is no longer staff, and has no permissions.
        self.akuma.is_active = False
        self.akuma.is_staff = False
        self.akuma.is_superuser = False

        # Create locations. These are used for clocking in and out
        self.loc1 = c_models.Location.objects.create(name='Japan')
        self.loc2 = c_models.Location.objects.create(name='America')
        self.loc3 = c_models.Location.objects.create(name='Japan')

        # Ip addresses, used for verifying punchclock locations
        self.ip1 = '000.000.00.00'
        self.ip2 = '123.456.78.90'
        self.ip3 = '111.222.33.44'

        # Punch clocks, where people can clock in.
        self.pc1 = c_models.Punchclock.objects.create(name='Rooftop', location=self.loc1, ip_address=self.ip1)
        self.pc2 = c_models.Punchclock.objects.create(name='Harbor', location=self.loc2, ip_address=self.ip2)
        self.pc3 = c_models.Punchclock.objects.create(name='Temple', location=self.loc3, ip_address=self.ip3)
        # Imitate a HTMLrequest object
        self.request = self.client

        # Save the fields to the test db to imitate the live site data.
        self.ryu.save()
        self.ken.save()
        self.akuma.save()
        self.loc1.save()
        self.loc2.save()
        self.loc3.save()
        self.pc1.save()
        self.pc2.save()
        self.pc3.save()


class ModelsTestCase(StartTestCase):
    """
    Test the models for Chronos. Add / edit any test.
    """
    def test_location(self):
        # Should be true
        self.assertEqual(self.loc1.name, 'Japan')
        self.assertEqual(self.loc2.name, 'America')
        self.assertEqual(self.loc3.name, 'Japan')

    def test_punchclock(self):
        # Should be true
        self.assertEqual(self.pc1.location.name, 'Japan')
        self.assertNotEqual(self.pc2.location, 'Japan')
        self.assertIsNotNone(c_models.Punchclock.objects.get(name='Rooftop'))


class ClockInClockOutTestCase(StartTestCase):
    """
    Test if users are properly clocking in and out.
    """
    def test_clockin(self):
        # self.request.method = 'POST'
        pass


class ShiftsTestCase(StartTestCase):

    """ Test shifts. Make sure we are grabbing the right ones. Either create
    shifts or use ones from the db.
    """
    def setUp(self):
        super(ShiftsTestCase, self).setUp()
        person = self.ryu
        intime = datetime(2011, 1, 1, 8, 0)
        shift = c_models.Shift(person=person, intime=intime)
        shift.save()

    def test_get_correct_shifts(self):
        year = 2011
        month = 1
        day = 1
        user = self.ryu
        week = 1
        payperiod = 1

        self.assertIsNotNone(c_views.get_shifts(year, month, day, user, week, payperiod))
        self.assertIsNotNone(c_views.get_shifts(year, month, None, None, None, None))


class LateTableCase(TestCase):
    """
    Test that the late table is receiving correct information to display.
    """
    def test_on_time(self):
        from mock import patch

        chronos = []
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25294, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '11:30:27', 'comm_out': u'OUT: ', 'out': '14:45:37'}
        chronos.append(pclock)

        date = '1927-11-04'

        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = [{'name': u'User 1', 'netid': 'user1'}]

        self.assertEqual(results, ([], expected_conflicts))

    def test_slighlty_early(self):

        from mock import patch
        import datetime

        chronos = []
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25294, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '11:28:27', 'comm_out': u'OUT: ', 'out': '14:45:37'}
        chronos.append(pclock)

        date = '1927-11-03'

        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = [{'clock_in': '11:28:27', 'sched_out': '14:45:00', 'clock_out': '14:45:37', 'comm_out': u'OUT: ', 'sched_in': '11:30:00', 'netid': 'user1', 'diff_in_early': datetime.timedelta(0, 93), 'name': u'User 1', 'comm_in': u'IN: '}]

        self.assertEquals(results, ([], expected_conflicts))

    def test_slightly_late(self):
        from mock import patch
        import datetime

        chronos = []

        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25294, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '11:30:27', 'comm_out': u'OUT: ', 'out': '14:46:37'}
        chronos.append(pclock)

        date = '1927-03-11'

        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = [{'clock_in': '11:30:27', 'sched_in': '11:30:00', 'diff_out_late': datetime.timedelta(0, 97), 'comm_in': u'IN: ', 'clock_out': '14:46:37', 'netid': 'user1', 'name': u'User 1', 'sched_out': '14:45:00', 'comm_out': u'OUT: '}]

        self.assertEqual(results, ([], expected_conflicts))

    def test_similar_shifts(self):
        from mock import patch
        import datetime

        chronos = []

        # This shift was worked the day before the day being examined--date = '1927-03-11'
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25291, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '18:49:20', 'comm_out': u'OUT: ', 'out': '22:21:25'}

        chronos.append(pclock)
        pclock = {}

        # This shift was worked on date being examined--date = '1927-03-11'
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25261, 'punchclock_in_location': u'Odega    ard Help Desk', 'name': u'User 1', 'in': '09:12:41', 'comm_out': u'OUT: ', 'out': '14:02:06'}
        chronos.append(pclock)

        date = '1927-03-11'
        service = 'dummy_service'

        # This shift was supposed to be worked on date being examined
        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "22:15:00", "In": "20:45:00", "Shift": 1}]}}):
            request = c_utils.compare(chronos, date, service)

        expected_conflict = []

        expected_no_show = [{'In': '20:45:00', 'Out': '22:15:00', 'Shift': 1, 'netid': 'user1'}]

        self.assertEqual(request, (expected_no_show, expected_conflict))

    def test_no_show(self):
        from mock import patch
        import datetime

        chronos = []

        date = '1927-03-11'

        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = []
        expected_no_shows = [{'In': '11:30:00', 'Out': '14:45:00', 'Shift': 1, 'netid': 'user1'}]

        self.assertEqual(results, (expected_no_shows, expected_conflicts))
