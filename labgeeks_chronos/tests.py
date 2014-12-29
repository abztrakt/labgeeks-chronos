""" Begin testing for Chronos, import proper libraries and models.
"""
from django.test import TestCase
from django.test.client import RequestFactory
from django.test import Client
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from labgeeks_chronos import models as c_models
from labgeeks_chronos import views as c_views
from labgeeks_chronos import utils as c_utils
from labgeeks_chronos import forms as c_forms
from mock import patch
import unittest
import string, random
import datetime


# Mock the datetime class

real_datetime_class = datetime.datetime

def mock_datetime_now(target, dt):
    import mock
    class DatetimeSubclassMeta(type):
        @classmethod
        def __instancecheck__(mcs, obj):
            return isinstance(obj, real_datetime_class)

    class BaseMockedDatetime(real_datetime_class):
        @classmethod
        def now(cls, tz=None):
            return target.replace(tzinfo=tz)

        @classmethod
        def utcnow(cls):
            return target
        
    # Python2 & Python3 compatible metaclass
    MockedDatetime = DatetimeSubclassMeta('datetime', (BaseMockedDatetime,), {})
        
    return mock.patch.object(dt, 'datetime', MockedDatetime)


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
        intime = datetime.datetime(2011, 1, 1, 8, 0)
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
        self.user1 = User.objects.create_user('user1', 'user1@uw.edu', 'coolestuser')
        self.user1.first_name = 'User'
        self.user1.last_name = '1'
        self.user1.is_active = True
        self.user1.is_staff = True
        self.user1.is_superuser = False
        self.user1.save()
        self.campus = c_models.Location.objects.create(name='Campus')
        self.pclock = c_models.Punchclock.objects.create(name='ode', location=self.campus, ip_address='0.0.0.0')

    def test_on_time(self):
        """
        Tests the instance that the student clocks in on time and leaves on time.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 11, 04, 11, 30, 27),
                                              outtime=datetime.datetime(1927, 11, 04, 14, 45, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-11-04'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1',
                               'netid': 'user1',
                               'comm_in': u'IN: ',
                               'comm_out': u'OUT: '}]
        expected_no_shows = []
        expected_missing_netids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_slightly_early(self):
        """
        Tests the instance that the student clocks in slightly early and leaves on time
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 11, 03, 11, 28, 27),
                                              outtime=datetime.datetime(1927, 11, 03, 14, 45, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
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
        expected_no_shows = []
        expected_missing_netids = []

        self.assertEquals(results, (expected_no_shows, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_slightly_late(self):
        """
        Tests the instance that the student clocks out slightly late and clocks in on time.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 11, 03, 11, 30, 00),
                                              outtime=datetime.datetime(1927, 11, 03, 14, 46, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
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
        expected_no_shows = []
        expected_missing_netids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_similar_shifts(self):
        """
        This test does not currently pass becuas there is a bug in the code. In the process of fixing it. Supposed to test the instance that the student has two shifts in a 24 hour time span but only works one of the shifts.
        """

        # This shift was worked the day before the day being examined--date = '1927-03-11'
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 11, 02, 18, 49, 20),
                                              outtime=datetime.datetime(1927, 11, 02, 22, 21, 25),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)

        date = '1927-11-03'
        service = 'dummy_service'

        # This shift was supposed to be worked on date being examined--'1927-11-03'
        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "22:15:00", "In": "20:45:00", "Shift": 1}]}}):
            request = c_utils.compare(date, service)

        expected_conflict = []

        expected_no_show = [{'In': '20:45:00',
                             'Out': '22:15:00',
                             'Shift': 1,
                             'name': 'User 1',
                             'netid': 'user1'}]
        expected_missing_netids = []

        self.assertEqual(request, (expected_no_show, expected_conflict, expected_missing_netids))
        shift.delete()

    def test_no_show(self):
        """
        Tests the instance when the student is scheduled to work a shift but does not work it.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 02, 11, 11, 30, 27),
                                              outtime=datetime.datetime(1927, 02, 11, 14, 46, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = []
        expected_no_shows = [{'In': '11:30:00',
                              'Out': '14:45:00',
                              'Shift': 1,
                              'name': 'User 1',
                              'netid': 'user1'}]
        expected_missing_netids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_another_no_show_case(self):
        """
        This test does not currently pass because of a bug in the code that I am working on fixing. Supposed to test when the shifts are more than 23 hours apart from each other but less than 24 hours.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 03, 12, 14, 12, 41),
                                              outtime=datetime.datetime(1927, 03, 12, 19, 02, 06),
                                              shiftnote='IN: \n\nOUT:',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = []
        expected_no_show = [{'In': '11:30:00',
                             'Out': '14:45:00',
                             'Shift': 1,
                             'name': 'User 1',
                             'netid': 'user1'}]
        expected_missing_netids = []

        self.assertEqual(results, (expected_no_show, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_24th_hour(self):
        """
        Tests that time is set to 00:00:00 when time  passed in is 24:00:00. This works but creates a bug.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 03, 11, 18, 49, 20),
                                              outtime=datetime.datetime(1927, 03, 11, 23, 59, 06),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)

        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "24:00:00", "In": "18:50:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1',
                               'netid': 'user1',
                               'comm_in': u'IN: ',
                               'comm_out': u'OUT: '}]
        expected_no_show = []
        expected_missing_netids = []

        self.assertEqual(results, (expected_no_show, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_out_early(self):
        """
        Test the instance when the student clocks in on time and clocks out early.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 06, 23, 18, 00, 00),
                                              outtime=datetime.datetime(1927, 06, 23, 23, 40, 00),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
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
        expected_missing_netids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_netids))
        shift.delete()

    def test_interpret_results(self):
        """
        Tests that the message that is passed back to the temaplate is correct.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 03, 11, 11, 30, 27),
                                              outtime=datetime.datetime(1927, 03, 11, 14, 46, 37),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            msg = c_utils.interpret_results(date, service)

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
        expected_missing_ids = []

        self.assertEqual(msg, (expected_msg, expected_missing_ids))
        shift.delete()

    def test_missing_netid(self):
        """ Tests the case that a user name returned from the api call that has a user who is not in the database.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 03, 11, 11, 30, 56),
                                              outtime=datetime.datetime(1927, 03, 11, 14, 46, 03),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={'Shifts': {'user_none': [{'Out': '14:45:00', 'In': '11:30:00', 'Shift': 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = []
        expected_no_shows = []
        expected_missing_netid = ['user_none']

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_netid))
        shift.delete()

    def test_shiftnote(self):
        """ Tests when the user deletes the auto filled 'IN: \n\nOUT: ' and putting their own
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 03, 11, 11, 30, 27),
                                              outtime=datetime.datetime(1927, 03, 11, 14, 46, 37),
                                              shiftnote='I deleted the auto filled stuff and put my own note',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "14:45:00", "In": "11:30:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'clock_in': '11:30:27',
                               'sched_out': '14:45:00',
                               'clock_out': '14:46:37',
                               'comm_out': u'',
                               'sched_in': '11:30:00',
                               'netid': 'user1',
                               'diff_out_late': datetime.timedelta(0, 97),
                               'name': u'User 1',
                               'comm_in': u'I deleted the auto filled stuff and put my own note'}]
        expected_no_shows = []
        expected_missing_ids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_ids))
        shift.delete()

    def test_overnight_shift(self):

        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 03, 11, 22, 15, 00),
                                              outtime=datetime.datetime(1927, 03, 12, 2, 15, 00),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-03-11'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "02:15:00", "In": "22:15:00", "Shift": 1}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1',
                               'netid': 'user1',
                               'comm_in': u'IN: ',
                               'comm_out': u'OUT: '}]
        expected_no_shows = []
        expected_missing_ids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_ids))
        shift.delete()

    def test_no_show_and_conflict(self):
        """ Tests when the user is scheduled for two shifts in one day but only works one of the shifts.
        """
        shift = c_models.Shift.objects.create(person=self.user1,
                                              intime=datetime.datetime(1927, 12, 19, 9, 30, 35),
                                              outtime=datetime.datetime(1927, 12, 19, 11, 30, 20),
                                              shiftnote='IN: \n\nOUT: ',
                                              in_clock=self.pclock,
                                              out_clock=self.pclock)
        date = '1927-12-19'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "11:30:00", "In": "09:30:00", "Shift": 1}, {"Out": "18:00:00", "In": "15:00:00", "Shift": 2}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1',
                               'netid': 'user1',
                               'comm_in': u'IN: ',
                               'comm_out': u'OUT: '}]
        expected_no_shows = [{'In': '15:00:00',
                              'Out': '18:00:00',
                              'Shift': 2,
                              'name': u'User 1',
                              'netid': 'user1'}]
        expected_missing_ids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_ids))

    def test_no_show_and_conflicts_2(self):
        """ Tests when the user if scheduled for 3 shifts in one day but only shows up for two shifts.
        """
        shift1 = c_models.Shift.objects.create(person=self.user1,
                                               intime=datetime.datetime(1927, 12, 22, 8, 30, 35),
                                               outtime=datetime.datetime(1927, 12, 22, 10, 30, 11),
                                               shiftnote='IN: \n\nOUT: ',
                                               in_clock=self.pclock,
                                               out_clock=self.pclock)
        shift2 = c_models.Shift.objects.create(person=self.user1,
                                               intime=datetime.datetime(1927, 12, 22, 19, 30, 25),
                                               outtime=datetime.datetime(1927, 12, 22, 22, 30, 45),
                                               shiftnote='IN: \n\nOUT: ',
                                               in_clock=self.pclock,
                                               out_clock=self.pclock)
        date = '1927-12-22'
        service = 'dummy_service'

        with patch.object(c_utils, 'read_api', return_value={"Shifts": {"user1": [{"Out": "10:30:00", "In": "8:30:00", "Shift": 1}, {"Out": "15:30:00", "In": "13:30:00", "Shift": 2}, {"Out": "22:30:00", "In": "19:30:00", "Shift": 3}]}}):
            results = c_utils.compare(date, service)

        expected_conflicts = [{'name': u'User 1',
                               'netid': 'user1',
                               'comm_in': u'IN: ',
                               'comm_out': u'OUT: '},
                              {'name': u'User 1',
                               'netid': 'user1',
                               'comm_in': u'IN: ',
                               'comm_out': u'OUT: '}]
        expected_no_shows = [{'In': '13:30:00',
                              'Out': '15:30:00',
                              'Shift': 2,
                              'name': u'User 1',
                              'netid': 'user1'}]
        expected_missing_ids = []

        self.assertEqual(results, (expected_no_shows, expected_conflicts, expected_missing_ids))
        shift1.delete()
        shift2.delete()

    def tearDown(self):
        """
        destroys all the objects that were created for each test.
        """
        self.user1.delete()
        self.campus.delete()
        self.pclock.delete()

class PunchclockTests(TestCase):

    def setUp(self):
        user2 = User.objects.create_user('user2', 'user2@uw.edu', 'punchclock')
        user2.first_name = 'User'
        user2.last_name = '2'
        user2.is_active = True
        user2.is_staff = True
        user2.is_superuser = False
        user2.save()
        campus = c_models.Location.objects.create(name='Campus')
        pclock = c_models.Punchclock.objects.create(name='ode', location=campus, ip_address='0.0.0.0')
        

    def test_clock_in_everything_correct(self):
        """
        Tests time() function for clocking in with everything correct -- Method = POST
        """
        # Get the user created in setUp()
        user2 = User.objects.get(username='user2')

        # Make up a random string with 10 characters
        length = 10 
        shift_in_note_random = ''.join(random.choice(string.lowercase) for i in range(length))

        # Use test client. First login
        client = Client()
        client.login(username='user2', password='punchclock')
       
        # Patch the output of datetime.now() so that we can assert the redirect url
        target = datetime.datetime(1927, 10, 15, 3, 45)
        with mock_datetime_now(target, datetime):
            response = client.post('/chronos/time/',  {'shiftnote' : shift_in_note_random}, REMOTE_ADDR='0.0.0.0')
           
        # HTTP 302 due to URL redirection
        self.assertEqual(response.status_code, 302)
        # Returning a QuerySet
        shift_created = c_models.Shift.objects.filter(person=user2, outtime=None)
        # We want the Shift object
        shift_created = shift_created[0]
        self.assertEqual(shift_created.shiftnote, shift_in_note_random)

        success = 'IN'
        at_time = '1927-10-15,%203:45%20AM' # %20 represents a space
        location = 'Campus'
        person = 'user2'
        self.assertRedirects(response, "chronos/time/success/?success=%s&at_time=%s&location=%s&user=%s" % (success, at_time, location, person))

    def test_clock_out_everything_correct(self):

        user2 = User.objects.get(username='user2')

        # Use test client. First login
        client = Client()
        client.login(username='user2', password='punchclock')
        
        # Make up a random string with 10 characters
        length = 10 
        shift_in_note_random = ''.join(random.choice(string.lowercase) for i in range(length))
        shift_out_note_random = ''.join(random.choice(string.lowercase) for i in range(length))

        # Patch the output of datetime.now() so that we can assert the redirect url
        # clock in
        target = datetime.datetime(1927, 10, 15, 3, 45)
        with mock_datetime_now(target, datetime):
            response = client.post('/chronos/time/',  {'shiftnote' : shift_in_note_random}, REMOTE_ADDR='0.0.0.0')

        # clock out
        target = datetime.datetime(1927, 10, 15, 5, 45)
        with mock_datetime_now(target, datetime):
            response = client.post('/chronos/time/',  {'shiftnote' : shift_out_note_random}, REMOTE_ADDR='0.0.0.0')

        # Get the shift obejct again, see if it has the expected note
        shift_created = c_models.Shift.objects.filter(person=user2)
        shift_created = shift_created[0]
        expected_note = "IN: %s\n\nOUT: %s" % (shift_in_note_random, shift_out_note_random)
        # We want the Shift object        
        self.assertEqual(shift_created.shiftnote, expected_note)

        success = 'OUT'
        at_time = '1927-10-15,%205:45%20AM' # %20 represents a space
        location = 'Campus'
        person = 'user2'
        self.assertRedirects(response, "chronos/time/success/?success=%s&at_time=%s&location=%s&user=%s" % (success, at_time, location, person))

    def test_fail_without_message_in_request(self):
        """
        Test fail() function; See if it behaves properly without giving message
        """
        user2 = User.objects.get(username='user2')

        # Use test client. First login
        client = Client()
        client.login(username='user2', password='punchclock')
        
        # GET into /chronos/time/fail, where fail() gets called; Provide 'reason', 'log_msg', but no 'message'
        reason = 'I am sick'
        log_msg = 'punchpara'
        
        # Because I do not provide message, I expect an error being thrown
        error_occured = False
        try:
            response = client.get("/chronos/time/fail/?reason=%s&log_msg=%s" % (reason, log_msg),  REMOTE_ADDR='0.0.0.0')
        except UnboundLocalError:
            # error is UnboundLocalError: local variable 'message' referenced before assignment
            error_occured = True

        self.assertTrue(error_occured)
        
    def test_fail_with_message_in_request(self):
        """
        Test fail() function; See if it behaves properly giving message
        """
        user2 = User.objects.get(username='user2')

        # Use test client. First login
        client = Client()
        client.login(username='user2', password='punchclock')
        
        # GET into /chronos/time/fail, where fail() gets called; Provide 'reason', 'log_msg', but no 'message'
        message = 'You should go and see the doctor'
        reason = 'I am sick'
        log_msg = 'punchparadox'
        
        # I do not expect an error being thrown
        error_occured = False
        try:
            response = client.get("/chronos/time/fail/?reason=%s&message=%s&log_msg=%s" % (reason, message, log_msg),  REMOTE_ADDR='0.0.0.0')
            self.assertEqual(response.status_code, 200)

            # I expect to see these in the response.content
            expect_html_title = "<h1>FAIL</h1>\n"
            expect_html_message = "<p>You should go and see the doctor</p>\n"
            expect_html_reason = "<p>I am sick</p>\n"
            expect_html_log_msg = "href=\"/punchparadox/\""

            content = response.content
            contains = (content.find(expect_html_title) != -1) & (content.find(expect_html_message) != -1)  & (content.find(expect_html_reason) != -1) & (content.find(expect_html_log_msg) != -1)

            self.assertTrue(contains)
            
        except UnboundLocalError:
            # error is UnboundLocalError: local variable 'message' referenced before assignment
            error_occured = True

        self.assertFalse(error_occured)

    def test_success_clock_in_everything_correct(self):
        """
        Test success() function for clock in everything correct
        """
        user2 = User.objects.get(username='user2')
                
        # Use test client. First login
        client = Client()
        client.login(username='user2', password='punchclock')
        
        # GET into /chronos/time/fail, where fail() gets called; Provide 'reason', 'log_msg', but no 'message'
        success = 'IN'
        at_time = '1927-10-15,%203:45%20AM' # %20 represents a space
        location = 'Campus'
        person = 'user2'
        
        response = client.get("/chronos/time/success/?success=%s&at_time=%s&location=%s&user=%s" % (success, at_time, location, person),  REMOTE_ADDR='0.0.0.0')
        self.assertEqual(response.status_code, 200)

        # I expect to see these in the response.content
        # user2 is appearing as user2@uw.edu --> it will be there as long as you did client.login
        expect_html_at_time = "<h3>The date and time recorded: 1927-10-15, 3:45 AM.</h3>\n"
        expect_html_success_location = "<span style=\"color:green\">IN</span>: Campus."

        content = response.content
        contains = (content.find(expect_html_at_time) != -1) & (content.find(expect_html_success_location) != -1)

        self.assertTrue(contains)

    def test_success_clock_out_everything_correct(self):
        """
        Test success() function for clock out everything correct
        """
        user2 = User.objects.get(username='user2')
                
        # Use test client. First login
        client = Client()
        client.login(username='user2', password='punchclock')
        
        # GET into /chronos/time/fail, where fail() gets called; Provide 'reason', 'log_msg', but no 'message'
        success = 'OUT'
        at_time = '1927-10-15,%203:45%20AM' # %20 represents a space
        location = 'Campus'
        person = 'user2'
        
        response = client.get("/chronos/time/success/?success=%s&at_time=%s&location=%s&user=%s" % (success, at_time, location, person),  REMOTE_ADDR='0.0.0.0')
        self.assertEqual(response.status_code, 200)

        # I expect to see these in the response.content
        # user2 is appearing as user2@uw.edu --> it will be there as long as you did client.login
        expect_html_at_time = "<h3>The date and time recorded: 1927-10-15, 3:45 AM.</h3>\n"
        expect_html_success_location = "<span style=\"color:red\">OUT</span>: Campus."

        content = response.content
        contains = (content.find(expect_html_at_time) != -1) & (content.find(expect_html_success_location) != -1)

        self.assertTrue(contains)

    def breakDown(self):
        user2.delete()
        location.delete()
        pclock.delete()
