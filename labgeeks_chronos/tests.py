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
        """
        Creates a user, campus, and punchclock for tests to be run with.
        """
        user1 = User.objects.create_user('user1', 'user1@uw.edu', 'coolestuser')
        user1.first_name = 'User'
        user1.last_name = '1'
        user1.is_active = True
        user1.is_staff = True
        user1.is_superuser = False
        user1.save()
        campus = c_models.Location.objects.create(name='Campus')
        pclock = c_models.Punchclock.objects.create(name='ode', location=campus, ip_address='0.0.0.0')

    def test_on_time(self):
        """
        Tests the instance that the student clocks in on time and leaves on time.
        """
        from mock import patch

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime(1927, 11, 04, 11, 30, 27),
                                              outtime=datetime(1927, 11, 04, 14, 45, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-11-04'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1',
                               'netid': 'user1'}]

        self.assertEqual(results, ([], expected_conflicts))
        del shift

    def test_slightly_early(self):
        """
        Tests the instance that the student clocks in slightly early and leaves on time
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 11, 03, 11, 28, 27),
                                              outtime=datetime.datetime(1927, 11, 03, 14, 45, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-11-03'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '11:28:27',
                               'sched_out': '14:45:00',
                               'clock_out': '14:45:37',
                               'comm_out': u'OUT: ',
                               'sched_in': '11:30:00',
                               'netid': 'user1',
                               'diff_in_early': datetime.timedelta(0, 93),
                               'name': u'User 1',
                               'comm_in': u'IN: '}]

        self.assertEquals(results, ([], expected_conflicts))
        del shift

    def test_slightly_late(self):
        """
        Tests the instance that the student clocks out slightly late and clocks in on time.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 11, 03, 11, 30, 00),
                                              outtime=datetime.datetime(1927, 11, 03, 14, 46, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-11-03'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '11:30:00',
                               'sched_in': '11:30:00',
                               'diff_out_late': datetime.timedelta(0, 97),
                               'comm_in': u'IN: ',
                               'clock_out': '14:46:37',
                               'netid': 'user1',
                               'name': u'User 1',
                               'sched_out': '14:45:00',
                               'comm_out': u'OUT: '}]

        self.assertEqual(results, ([], expected_conflicts))
        del shift

    def test_similar_shifts(self):
        """
        This test does not currently pass becuas there is a bug in the code. In the process of fixing it. Supposed to test the instance that the student has two shifts in a 24 hour time span but only works one of the shifts.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')

        # This shift was worked the day before the day being examined--date = '1927-03-11'
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 11, 02, 18, 49, 20),
                                              outtime=datetime.datetime(1927, 11, 02, 22, 21, 25),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)

        date = '1927-11-03'
        service = 'dummy_service'

        # This shift was supposed to be worked on date being examined--'1927-11-03'
        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "22:15:00", "In": "20:45:00", "Shift": 1}]}}):
            request = c_utils.compare(date, service)

        expected_conflict = []

        expected_no_show = [{'In': '20:45:00',
                             'Out': '22:15:00',
                             'Shift': 1,
                             'netid': 'user1'}]

        self.assertEqual(request, (expected_no_show, expected_conflict))
        del shift

    def test_no_show(self):
        """
        Tests the instance when the student is scheduled to work a shift but does not work it.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 03, 11, 11, 30, 27),
                                              outtime=datetime.datetime(1927, 03, 11, 14, 46, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = []
        expected_no_shows = [{'In': '11:30:00',
                              'Out': '14:45:00',
                              'Shift': 1,
                              'netid': 'user1'}]

        self.assertEqual(results, (expected_no_shows, expected_conflicts))
        del shift

    def test_another_no_show_case(self):
        """
        This test does not currently pass because of a bug in the code that I am working on fixing. Supposed to test when the shifts are more than 23 hours apart from each other but less than 24 hours.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 03, 11, 14, 12, 41),
                                              outtime=datetime.datetime(1927, 03, 11, 19, 02, 06),
                                              shiftnote='IN: \n\nOUT:',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = []
        expected_no_show = [{'In': '11:30:00',
                             'Out': '14:45:00',
                             'Shift': 1,
                             'netid': 'user1'}]

        self.assertEqual(results, (expected_no_show, expected_conflicts))
        del shift

    def test_24th_hour(self):
        """
        Tests that time is set to 00:00:00 when time  passed in is 24:00:00. This works but creates a bug.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 03, 11, 18, 49, 20),
                                              outtime=datetime.datetime(1927, 03, 11, 23, 59, 06),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)

        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "24:00:00", "In": "18:50:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '18:49:20',
                               'sched_out': '00:00:00',
                               'clock_out': '23:59:06',
                               'comm_out': u'OUT: ',
                               'sched_in': '18:50:00',
                               'netid': 'user1',
                               'diff_in_early': datetime.timedelta(0, 54),
                               'name': u'User 1',
                               'comm_in': u'IN: '}]
        expected_no_show = []

        self.assertEqual(results, (expected_no_show, expected_conflicts))
        del shift

    def test_out_early(self):
        """
        Test the instance when the student clocks in on time and clocks out early.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = _models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 06, 23, 18, 00, 00),
                                              outtime=datetime.datetime(1927, 06, 23, 23, 40, 00),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-06-23'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "23:45:00", "In": "18:00:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '18:00:00',
                               'sched_out': '23:45:00',
                               'clock_out': '23:40:00',
                               'comm_out': u'OUT: ',
                               'sched_in': '18:00:00',
                               'netid': 'user1',
                               'diff_out_early': datetime.timedelta(0, 300),
                               'name': u'User 1',
                               'comm_in': u'IN: '}]
        expected_no_shows = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts))
        del shift

    def test_interpet_results(self):
        """
        Tests that the message that is passed back to the temaplate is correct.
        """
        from mock import patch
        import datetime

        user1 = User.objects.get(username='user1')
        pclock = c_models.Punchclock.objects.get(name='ode')
        shift = c_models.Shift.objects.create(person=user1,
                                              intime=datetime.datetime(1927, 11, 03, 11, 30, 27),
                                              outtime=datetime.datetime(1927, 11, 03, 14, 46, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=pclock,
                                              out_clock=pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            msg = c_utils.interpet_results(date, service)

        expected_msg = [{'status': 'Clock Out Late',
                         'comm_in': u'IN: ',
                         'color': 'blacker',
                         'sched_in': '11:30 AM',
                         'clock_out': '02:46 PM',
                         'date': '1927-03-11',
                         'change': datetime.timedelta(0, 97),
                         'comm_out': u'OUT: ',
                         'clock_in': '11:30 AM',
                         'name': u'User 1',
                         'netid': 'user1',
                         'sched_out': '02:45 PM'}]

        self.assertEqual(msg, expected_msg)
        del shift

    def breakDown(self):
        """
        destroys all the objects that were created for each test.
        """
        user1.delete()
        location.delete()
        pclock.delete()
