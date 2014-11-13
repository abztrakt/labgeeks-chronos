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

    def setUp(self):
        user1 = User.objects.create_user('user1', 'user1@uw.edu', 'coolestuser')
        user1.name = 'User 1'
        user1.is_active = True
        user1.is_staff = True
        user.is_superuser = False
        user1.save()
        location = Location.objects.create()
        location.name = 'Campus'
        pclock = Punchclock.objects.create(name='ode', location=location, ip_address='0.0.0.0')

    def test_on_time(self):
        from mock import patch

        shift = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 04, 11, 30, 27), outtime=datetime.datetime(1927, 11, 04, 14, 45, 37), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)
        shift.save()
        date = '1927-11-04'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1', 'netid': 'user1'}]

        self.assertEqual(results, ([], expected_conflicts))
        shift.delete()

    def test_slighlty_early(self):
        from mock import patch
        import datetime

        shift = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 03, 11, 28, 27), outtime=datetime.datetime(1927, 11, 03, 14, 45, 37), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)
        shift.save()
        date = '1927-11-03'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '11:28:27', 'sched_out': '14:45:00', 'clock_out': '14:45:37', 'comm_out': u'OUT: ', 'sched_in': '11:30:00', 'netid': 'user1', 'diff_in_early': datetime.timedelta(0, 93), 'name': u'User 1', 'comm_in': u'IN: '}]

        self.assertEquals(results, ([], expected_conflicts))
        shift.delete()

    def test_slightly_late(self):
        from mock import patch
        import datetime

        shift = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 03, 11, 30, 27), outtime=datetime.datetime(1927, 11, 03, 14, 46, 37), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)
        shift.save()
        date = '1927-11-03'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '11:30:27', 'sched_in': '11:30:00', 'diff_out_late': datetime.timedelta(0, 97), 'comm_in': u'IN: ', 'clock_out': '14:46:37', 'netid': 'user1', 'name': u'User 1', 'sched_out': '14:45:00', 'comm_out': u'OUT: '}]

        self.assertEqual(results, ([], expected_conflicts))
        shift.delete()

    def test_similar_shifts(self):
        from mock import patch
        import datetime

        # This shift was worked the day before the day being examined--date = '1927-03-11'
        shift1 = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 02, 18, 49, 20), outtime=datetime.datetime(1927, 11, 02, 22, 21, 25), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)

        # This shift was worked on date being examined--date = '1927-03-11'
        shift2 = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 03, 09, 12, 41), outtime=datetime.datetime(1927, 11, 03, 14, 02, 06), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)
        shift1.save()
        shift2.save()
        date = '1927-11-03'
        service = 'dummy_service'

        # This shift was supposed to be worked on date being examined
        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "22:15:00", "In": "20:45:00", "Shift": 1}]}}):
            request = c_utils.compare(date, service)

        expected_conflict = []

        expected_no_show = [{'In': '20:45:00', 'Out': '22:15:00', 'Shift': 1, 'netid': 'user1'}]

        self.assertEqual(request, (expected_no_show, expected_conflict))
        shift1.delete()
        shift2.delete()

    def test_no_show(self):
        from mock import patch
        import datetime

        shift = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 03, 11, 30, 27), outtime=datetime.datetime(1927, 11, 03, 14, 46, 37), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)
        shift.save()
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = []
        expected_no_shows = [{'In': '11:30:00', 'Out': '14:45:00', 'Shift': 1, 'netid': 'user1'}]

        self.assertEqual(results, (expected_no_shows, expected_conflicts))


    def test_another_no_show_case(self):
        from mock import patch
        import datetime

        chronos = []
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25261, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '14:12:41', 'comm_out': u'OUT: ', 'out': '19:02:06'}
        chronos.append(pclock)

        date = '1927-03-11'

        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = []
        expected_no_show = [{'In': '11:30:00', 'Out': '14:45:00', 'Shift': 1, 'netid': 'user1'}]

        self.assertEqual(results, (expected_no_show, expected_conflicts))

    def test_24th_hour(self):
        from mock import patch
        import datetime

        chronos = []
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25291, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '18:49:20', 'comm_out': u'OUT: ', 'out': '23:59:06'}
        chronos.append(pclock)

        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "24:00:00", "In": "18:50:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = [{'clock_in': '18:49:20', 'sched_out': '00:00:00', 'clock_out': '23:59:06', 'comm_out': u'OUT: ', 'sched_in': '18:50:00', 'netid': 'user1', 'diff_in_early': datetime.timedelta(0, 54), 'name': u'User 1', 'comm_in': u'IN: '}]
        expected_no_show = []

        self.assertEqual(results, (expected_no_show, expected_conflicts))

    def test_out_early(self):
        from mock import patch
        import datetime

        chronos = []
        pclock = {'comm_in': u'IN: ', 'netid': u'user1', 'shift': 25634, 'punchclock_in_location': u'Odegaard Help Desk', 'name': u'User 1', 'in': '18:00:00', 'comm_out': u'OUT: ', 'out': '23:40:00'}
        chronos.append(pclock)

        date = '1927-06-23'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "23:45:00", "In": "18:00:00", "Shift": 1}]}}):
            results = c_utils.compare(chronos, date, service)

        expected_conflicts = [{'clock_in': '18:00:00', 'sched_out': '23:45:00', 'clock_out': '23:40:00', 'comm_out': u'OUT: ', 'sched_in': '18:00:00', 'netid': 'user1', 'diff_out_early': datetime.timedelta(0, 300), 'name': u'User 1', 'comm_in': u'IN: '}]
        expected_no_shows = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts))


    def test_interpet_results(self):
        from mock import patch
        import datetime

        shift = Shift.objects.create(person=user1, intime=datetime.datetime(1927, 11, 03, 11, 30, 27), outtime=datetime.datetime(1927, 11, 03, 14, 46, 37), shiftnote='IN: OUT: ', in_clock=pclock, out_clock=pclock)

        shift.save()
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            msg = c_utils.interpet_results(chronos, date, service)

        expected_msg = [{'status': 'Clock Out Late', 'comm_in': u'IN: ', 'color': 'blacker', 'sched_in': '11:30 AM', 'clock_out': '02:46 PM', 'date': '1927-03-11', 'change': datetime.timedelta(0, 97), 'comm_out': u'OUT: ', 'clock_in': '11:30 AM', 'name': u'User 1', 'netid': 'user1', 'sched_out': '02:45 PM'}]

        self.assertEqual(msg, expected_msg)

    def breakDown(self):
        user1.delete()
        location.delete()
        pclock.delete()
>>>>>>> Adjusted the tests to work with bug fix to late table. Fixing SDEV-538
