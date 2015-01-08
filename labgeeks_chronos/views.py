from django.contrib.auth.decorators import login_required
from django.core.context_processors import csrf
from django.shortcuts import render_to_response, get_object_or_404, \
    HttpResponseRedirect
from django.template import RequestContext
from labgeeks_chronos.forms import LateForm, ShiftForm, DataForm, HourForm
from labgeeks_chronos.models import Shift, Punchclock
from random import choice
from labgeeks_chronos.utils import *
from labgeeks.utils import ReportCalendar, TimesheetCalendar
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from labgeeks_people.models import UserProfile
from django.http import HttpResponse, HttpResponseBadRequest
from django.template import loader, Context
from django.shortcuts import render
from operator import itemgetter
import collections
from collections import defaultdict
import calendar
from django.template import RequestContext
import datetime

def list_options(request):
    """ Lists the options that users can get to when using chronos.
    """

    params = {'request': request}
    return render_to_response('options.html', params, context_instance=RequestContext(request))


def monthly_list_shifts(request, user, year, month):
    """ Lists the monthly shifts/timesheets all together for an employee
    """
    params = {'request': request}
    mname = calendar.month_name[int(month)]
    params['mname'] = mname
    user = User.objects.get(username=user)
    params['user'] = user
    shifts = Shift.objects.filter(intime__year=int(year), intime__month=int(month), person=user)
    params['shifts'] = shifts
    return render_to_response('monthly_list_shifts.html', params)


def csv_daily_data(request, year, month, day):
    """ Lets you download csv data for a particular date
    """
    shifts = get_shifts(year, month, day)
    response = csv_data_generator(shifts, year, month, day)
    return response


@login_required
def late_tool(request):
    """ Generates a form for displaying team members who were late
    """
    params = {'request': request}
    if not request.user.is_staff:
        message = 'Permission Denied'
        reason = 'You do not have permission to visit this part of the page.'
        return render_to_response('fail.html', params)

    if request.method == 'POST':
        form = LateForm(request.POST)
        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            service = form.cleaned_data['service']
            end_date = form.cleaned_data['end_date']

            if not end_date:
                end_date = start_date

            return HttpResponseRedirect('latetable?start_date={0}&end_date={1}&service={2}'.format(start_date, end_date, service))
    else:
        form = LateForm()
    return render_to_response('late_tool.html', locals(), context_instance=RequestContext(request))


@login_required
def late_table(request):
    """ Displays a table of late students with appropriate status
    """

    if not request.user.is_staff:
        message = 'Permission Denied'
        reason = 'You do not have permission to visit this part of the page.'

        return render_to_response('fail.html', locals())

    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    service = request.GET.get('service', '')

    start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
    shift_data = {}
    students_msg = []
    students_missing_netids = set()
    dates = []

    for each_day in range(int((end_date - start_date).days)):
        start = start_date
        num = each_day + 1
        end = start_date + datetime.timedelta(days=num)
        shifts_for_day = Shift.objects.filter(intime__gte=start.strftime("%Y-%m-%d %X"), outtime__lte=end.strftime("%Y-%m-%d 04:00:00"))
        curr_date = start_date + datetime.timedelta(days=each_day)
        dates.append(curr_date)
        shift_data[curr_date] = shifts_for_day

    for date, shifts in shift_data.items():
        date = datetime.date.strftime("%Y-%m-%d")
        response = interpret_results(date, service)
        students_msg.append(response[0])
        for netid in response[1]:
            students_missing_netids.add(netid)

    start_date_display = start_date.strftime("%b. %d, %Y")
    end_date_display = end_date - datetime.timedelta(days=1)
    end_date_display = end_date_display.strftime("%b. %d, %Y")

    return render_to_response('late_table.html', locals(), context_instance=RequestContext(request))


def csv_data_former(request):
    """ Generates a form for downloading a particular time period
        shifts in CSV format.
    """
    params = {'request': request}
    if not request.user.is_staff:
        params['message'] = 'Permission Denied'
        params['reason'] = 'You do not have permission to visit this part of the page.'
        return render_to_response('fail.html', params)

    if request.method == 'POST':
        form = DataForm(request.POST)
        if form.is_valid():
            end_date = form.cleaned_data['end_date']
            start_date = form.cleaned_data['start_date']
            shifts = Shift.objects.filter(intime__gte=start_date.strftime("%Y-%m-%d %X"), outtime__lte=end_date.strftime("%Y-%m-%d 23:59:59"))
            response = csv_data_generator(shifts, end_date=end_date, start_date=start_date)
            return response
    else:
        form = DataForm()
        params['form'] = form
    return render_to_response('csv_form.html', params, context_instance=RequestContext(request))


def csv_data_generator(shifts, year=None, month=None, day=None, end_date=None, start_date=None):
    """ Helper function to generate and download shift data
    """
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename = "chronos.csv"'
    temp = []
    for i in shifts:
        temp.append(i.person)
    all_people_working = set(temp)

    shifter = defaultdict(list)
    for worker in all_people_working:
        if end_date and start_date:
            shifts_per_person = Shift.objects.filter(intime__gte=start_date.strftime("%Y-%m-%d %X"), outtime__lte=end_date.strftime("%Y-%m-%d 23:59:59"), person=worker)
        elif year and month and day:
            shifts_per_person = Shift.objects.filter(intime__year=int(year), intime__month=int(month), intime__day=int(day), person=worker)
        else:
            shifts_per_person = Shift.objects.all()

        counter = 1
        for each in shifts_per_person:
            # Splits up shiftnotes into two separate variables if there are two to
            # begin with

            if "\n\n" in each.shiftnote:
                shiftnotes = each.shiftnote.split("\n\n")
                each.shiftinnote = shiftnotes[0]
                each.shiftoutnote = shiftnotes[1]
            else:
                each.shiftinnote = each.shiftnote
                each.shiftoutnote = ""

            if each.outtime is None:
                out = "Not Clocket Out"
            else:
                out = each.outtime.strftime("%X")
            data_shifts = [
                each.intime.strftime("%Y-%m-%d"),
                each.person.__str__(),
                each.intime.strftime("%X"),
                out,
                each.shiftinnote.__str__().lstrip('IN: '),
                each.shiftoutnote.__str__().lstrip('OUT: '),
                counter,
                each.in_clock.location,
            ]
            shifter[worker.__str__()].append(data_shifts)
            counter = counter + 1

    final_data = []
    for value in shifter.itervalues():
        for v in value:
            final_data.append(v)

    header = [
        "date",
        "netid",
        "in",
        "out",
        "comm_in",
        "comm_out",
        "shift",
        "punchclock_in_location",
    ]
    sorted_data = sorted(final_data, key=itemgetter(1))
    sorted_data.insert(0, header)
    t = loader.get_template('csv_template.txt')
    c = Context({
                'data': sorted_data,
                }
                )
    response.write(t.render(c))
    return response


def get_total_hours(request):
    """This method returns the cumulative hours worked by all employees in the
       range entered by the user in the form.
    """
    params = {'request': request}
    if request.method == 'POST':
        form = HourForm(request.POST)
        params['form'] = form
        if form.is_valid():
            end_date = form.cleaned_data['end_date']
            start_date = form.cleaned_data['start_date']
            shifts = Shift.objects.filter(intime__gte=start_date.strftime("%Y-%m-%d %X"), outtime__lte=end_date.strftime("%Y-%m-%d 23:59:59"))
            temp = []
            for i in shifts:
                temp.append(i.person)
            all_people_working = set(temp)
            all_people_working = list(all_people_working)
            shifter = defaultdict(list)
            totaler = []
            for worker in all_people_working:
                shifts_per_person = Shift.objects.filter(intime__gte=start_date.strftime("%Y-%m-%d %X"), outtime__lte=end_date.strftime("%Y-%m-%d 23:59:59"), person=worker)
                total = 0.0
                for each in shifts_per_person:
                    total = total + float(each.length())
                total_per_person = [
                    worker.__str__(),
                    round(total, 2),
                ]
                totaler.append(total_per_person)

            params['totaler'] = totaler
            return render_to_response('total_hours.html', params, context_instance=RequestContext(request))
    else:
        form = DataForm()
        params['form'] = form
    return render_to_response('total_hours.html', params, context_instance=RequestContext(request))


def get_shifts(year, month, day=None, user=None, week=None, payperiod=None):
    """ This method is used to return specific shifts
        Since the calendar model is used, year and month both need to be given
        The day, user, week, and payperiod parameters are optional and only used for detailed shifts.
    """
    if day and user:
        # We are grabing a specific user's day shift.
        shifts = Shift.objects.filter(intime__year=int(year), intime__month=int(month), intime__day=int(day), person=user)
    elif day:
        # We are grabing total shifts in a day
        shifts = Shift.objects.filter(intime__year=int(year), intime__month=int(month), intime__day=int(day))
    elif user:
        # We are grabing all of the user's shift in the given month and year
        shifts = Shift.objects.filter(intime__year=int(year), intime__month=int(month), person=user)
    else:
        # We are grabing all of the total shifts in the given month and year.
        shifts = Shift.objects.filter(intime__year=int(year), intime__month=int(month))

    if week:
        # Filter the shifts by the given week of the month (i.e. week=1 means
        # grab shifts in 1st week of month)
        first_week = datetime.date(int(year), int(month), 1).isocalendar()[1]

        # TODO: fix this hack to get around isocaledar's first week of the year
        # wierdness. See #98
        if first_week == 52 and int(month) == 1:
            first_week = 1

        weekly = {}
        for shift in shifts:
            shift_date = shift.intime
            this_week = shift_date.isocalendar()[1]
            if this_week == 52 and int(month) == 1:
                this_week = 1
            week_number = this_week - first_week + 1
            if week_number in weekly:
                weekly[week_number].append(shift)
            else:
                weekly[week_number] = [shift]
        shifts = weekly[int(week)]
    elif payperiod:
        # Filter the shifts by the given payperiod of the month
        # (i.e. payperiod=1 means grab shifts in 1st payperiod of month)
        payperiod_shifts = {'first': [], 'second': []}
        for shift in shifts:
            shift_date = shift.intime
            if shift_date.day <= 15:
                payperiod_shifts['first'].append(shift)
            else:
                payperiod_shifts['second'].append(shift)

        if int(payperiod) == 1:
            shifts = payperiod_shifts['first']
        else:
            shifts = payperiod_shifts['second']

    # Return the correct shifts
    return shifts


def calc_shift_stats(shifts, year, month):
    """ This method returns various calculations regarding a collection of
    shifts in a given year and month.
    """
    payperiod_totals = {'first': 0, 'second': 0}
    weekly = {}
    first_week = datetime.date(year, month, 1).isocalendar()[1]

    # TODO: fix this hack around isocalendars calculating first week of the
    # year, see #98
    if first_week == 52 and month == 1:
        first_week = 1

    for shift in shifts:
        week_number = shift.intime.isocalendar()[1] - first_week + 1

        if week_number not in weekly:
            weekly[week_number] = 0

        if shift.outtime:
            shift_date = shift.intime
            length = float(shift.length())

            # Keep track of pay period totals
            if shift_date.day <= 15:
                # 1st pay period
                payperiod_totals['first'] += length
            else:
                # 2nd pay period
                payperiod_totals['second'] += length

            weekly[week_number] += length

    # Sort the weekly totals
    weeks = weekly.keys()
    weeks.sort()
    weekly_totals = []
    for i in range(0, len(weeks)):
        weekly_totals.append({'week': weeks[i], 'total': weekly[weeks[i]]})

    result = {
        'weeks': weeks,
        'weekly_totals': weekly_totals,
        'payperiod_totals': payperiod_totals,
    }

    return result


def prev_and_next_dates(year, month):
    """ This method returns a previous and upcomming months from a given month
    and year.
    """
    # Figure out the prev and next months
    if month == 1:
        # Its January
        prev_date = datetime.date(year - 1, 12, 1)
        next_date = datetime.date(year, 2, 1)
    elif month == 12:
        # Its December
        prev_date = datetime.date(year, 11, 1)
        next_date = datetime.date(year + 1, 1, 1)
    else:
        # Its a regular month
        prev_date = datetime.date(year, month - 1, 1)
        next_date = datetime.date(year, month + 1, 1)

    result = {'prev_date': prev_date, 'next_date': next_date}
    return result
    """ The methods and views below deal with OVERALL calendar information
    """


@login_required
def staff_report(request, year, month, day=None, user=None, week=None, payperiod=None):
    """ This view is used to display all shifts in a time frame. Only users
    with specific permissions can view this information.
    """
    staff_report_checker = True
    params = {'request': request}
    if not request.user.is_staff:
        params['message'] = 'Permission Denied'
        params['reason'] = 'You do not have permission to visit this part of the page.'
        return render_to_response('fail.html', params)

    return specific_report(request, user, year, month, day, week, payperiod, staff_report_checker)


@login_required
def specific_report(request, user, year, month, day=None, week=None, payperiod=None, staff_report_checker=None):
    """ This view is used when viewing specific shifts in the given day.
    """
    params = {'request': request}
    try:
        # Grab shifts
        if user:
            user = User.objects.get(username=user)
            params['user'] = user

            all_shifts = get_shifts(year, month, day, user, week, payperiod)
        if day:
            description = "Viewing shifts for %s." % (datetime.date(int(year), int(month), int(day)).strftime("%B %d, %Y"))
            all_shifts = get_shifts(year, month, day, user, week, payperiod)
        elif week:
            description = "Viewing shifts in week %d of %s." % (int(week), datetime.date(int(year), int(month), 1).strftime("%B, %Y"))
        else:
            # This should be a payperiod view
            description = "Viewing shifts in payperiod %d of %s." % (int(payperiod), datetime.date(int(year), int(month), 1).strftime("%B, %Y"))
            params['description'] = description
    except:
        template = loader.get_template('400.html')
        context = RequestContext(request, {'request': request})
        return HttpResponseBadRequest(template.render(context))

    # The following code is used for displaying the user's call_me_by or first
    # name.
    shifts = []
    for shift in all_shifts:
        if "\n\n" in shift.shiftnote:
            shiftnotes = shift.shiftnote.split("\n\n")
            shift.shiftinnote = shiftnotes[0]
            shift.shiftoutnote = shiftnotes[1]
        else:
            shift.shiftinnote = shift.shiftnote
            shift.shiftoutnote = ""

        user = User.objects.get(username=shift.person)
        try:
            profile = UserProfile.objects.get(user=user)

            if profile.call_me_by:
                user = profile.call_me_by
            else:
                user = user.first_name
        except UserProfile.DoesNotExist:
            user = user.first_name

        # Splits up shiftnotes into two separate variables if there are two to
        # begin with
        if "\n\n" in shift.shiftnote:
            shiftnotes = shift.shiftnote.split("\n\n")
            shift.shiftinnote = shiftnotes[0]
            shift.shiftoutnote = shiftnotes[1]
        else:
            shift.shiftinnote = shift.shiftnote
            shift.shiftoutnote = ""

        data = {
            'person': user,
            'location': shift.in_clock.location,
            'intime': shift.intime,
            'outtime': shift.outtime,
            'length': shift.length,
            'shiftinnote': shift.shiftinnote,
            'shiftoutnote': shift.shiftoutnote,
        }
        shifts.append(data)
    params['shifts'] = shifts

    return render_to_response('specific_report.html', params, context_instance=RequestContext(request))


@login_required
def report(request, user=None, year=None, month=None):
    """ Creates a report of shifts in the year and month.
    """

    params = {'request': request}
    if not request.user.is_staff:
        params['message'] = 'Permission Denied'
        params['reason'] = 'You do not have permission to visit this part of the page.'
        return render_to_response('fail.html', params)

    # Initiate the return argument list
    args = {}

    # Grab shifts
    if not year:
        year = datetime.date.today().year
    if not month:
        month = datetime.date.today().month
    year = int(year)
    month = int(month)
    shifts = get_shifts(year, month, None, user)

    # Calculate the previous and upcomming months.
    prev_and_next = prev_and_next_dates(year, month)
    prev_date = prev_and_next['prev_date']
    next_date = prev_and_next['next_date']

    # Create calendar and compute stats
    calendar = mark_safe(ReportCalendar(shifts, user=user).formatmonth(year, month))
    stats = calc_shift_stats(shifts, year, month)
    weeks = stats['weeks']

    args = {
        'request': request,
        'year': year,
        'month': month,
        'calendar': calendar,
        'prev_date': prev_date,
        'next_date': next_date,
        'weeks': weeks,
        'today_year': datetime.date.today().year,
        'today_month': datetime.date.today().month,
    }

    return render_to_response('report.html', args, context_instance=RequestContext(request))


@login_required
def personal_report(request, user=None, year=None, month=None):
    """ Creates a personal report of all shifts for that user.
    """
    args = {}
    # Determine who the user is. This will return a calendar specific to that
    # person.
    if not user:
        user = request.user
    else:
        user = get_object_or_404(User, username=user)

    # If the year and month are not given, assume it is the current year &
    # month.
    if not year:
        year = datetime.date.today().year
    if not month:
        month = datetime.date.today().month

    year = int(year)
    month = int(month)
    if request.user.is_authenticated():
        # Grab user's shifts
        shifts = get_shifts(year, month, None, user)
        calendar = mark_safe(TimesheetCalendar(shifts, user=user).formatmonth(year, month))
    else:
        shifts = None
        calendar = None

    # Only has Clock IN or OUT link if computer is a punchclock
    current_ip = request.META['REMOTE_ADDR']
    punchclock_ips = []
    while len(punchclock_ips) < len(Punchclock.objects.all()):
        punchclock_ips.append(Punchclock.objects.values('ip_address')[len(punchclock_ips)]['ip_address'])
    if current_ip in punchclock_ips:
        is_a_punchclock = True
        punchclock_message = ["Clock IN or OUT"]
    else:
        is_a_punchclock = False
        punchclock_message = ["This machine is not a punch clock.",
                              "I'm sorry %s, I'm afraid I can't let you Clock IN or OUT from this machine." % user.first_name,
                              "You shall not pass (or Clock IN or OUT)!",
                              "The cake is a lie, and this box isn't a punch clock."]

    # Calculate the previous and upcomming months.
    prev_and_next = prev_and_next_dates(year, month)
    prev_date = prev_and_next['prev_date']
    next_date = prev_and_next['next_date']

    # Compute shift stats
    stats = calc_shift_stats(shifts, year, month)
    payperiod_totals = stats['payperiod_totals']
    weekly_totals = stats['weekly_totals']

    args = {
        'request': request,
        'user': user.username,
        'year': year,
        'month': month,
        'calendar': calendar,
        'prev_date': prev_date,
        'next_date': next_date,
        'weekly_totals': weekly_totals,
        'payperiod_totals': payperiod_totals,
        'today_year': datetime.date.today().year,
        'today_month': datetime.date.today().month,
        'is_a_punchclock': is_a_punchclock,
        'punchclock_message': choice(punchclock_message),
    }

    return render_to_response('options.html', args, context_instance=RequestContext(request))


@login_required
def time(request):
    """ Sign in or sign out of a shift.
    """
    params = {'request': request}
    # Generate a token to protect from cross-site request forgery
    c = {}
    c.update(csrf(request))

    # Grab information we want to pass along no matter what state we're in
    user = request.user
    params['user'] = user
    # Getting machine location user is currently using
    current_ip = request.META['REMOTE_ADDR']

    try:
        punchclock = Punchclock.objects.filter(ip_address=current_ip)[0]
    except:
        # implement bad monkey page redirect
        message = "You are a very bad monkey!"
        reason = "This computer isn't one of the punchclocks, silly..."
        log_msg = "Your IP Address, %s, has been logged and will be reported. (Just kidding. But seriously, you can't sign in or out from here.)" % current_ip
        return HttpResponseRedirect("fail/?message=%s&reason=%s&log_msg=%s" % (message, reason, log_msg))

    location = punchclock.location

    # Check for POST, if not blank form, if true 'take in data'
    if request.method == 'POST':
        form = ShiftForm(request.POST)
        # Check form data for validity, if not valid, fail gracefully
        if form.is_valid():
            # We are creating a shift object that we can manipulate
            # programatically later
            this_shift = form.save(commit=False)
            this_shift.person = request.user

            # Check whether user has open shift at this location
            if this_shift.person in location.active_users.all():
                try:
                    oldshift = Shift.objects.filter(person=request.user, outtime=None)
                    oldshift = oldshift[0]
                except IndexError:
                    message = "Whoa. Something wacky is up."
                    reason = "You appear to be signed in at %s, but don't have an open entry in my database. This is kind of a metaphysical crisis for me, I'm no longer sure what it all means." % location
                    log_msg = "punchparadox"
                    return HttpResponseRedirect("fail/?reason=%s&message=%s&log_msg=%s" % (reason, message, log_msg))
                oldshift.outtime = datetime.datetime.now()
                oldshift.shiftnote = "IN: %s\n\nOUT: %s" % (oldshift.shiftnote, form.data['shiftnote'])
                oldshift.out_clock = punchclock
                oldshift.save()
                location.active_users.remove(request.user)
                # Setting the success variable that users will see on success
                # page
                success = "OUT"
                at_time = oldshift.outtime
                # get rid of zeros on the hour
                at_time = at_time.strftime('%Y-%m-%d, %I:%M %p').replace(' 0', ' ')
            else:
                # if shift.person  location.active_staff
                if this_shift.intime is None:
                    this_shift.intime = datetime.datetime.now()
                this_shift.in_clock = punchclock
                # On success, save the shift
                this_shift.save()
                # After successful shift save, add person to active_staff in
                # appropriate Location
                location.active_users.add(this_shift.person)
                # Setting the success variable that users will see on the
                # success page
                success = "IN"
                at_time = this_shift.intime
                # get rid of zeros on the hour
                at_time = at_time.strftime('%Y-%m-%d, %I:%M %p').replace(' 0', ' ')

            return HttpResponseRedirect("success/?success=%s&at_time=%s&location=%s&user=%s" % (success, at_time, location, this_shift.person))

    # If POST is false, then return a new fresh form.
    else:
        form = ShiftForm()
        in_or_out = 'IN'
        if user in location.active_users.all():
            in_or_out = 'OUT'

    # The following code is used for displaying the user's call_me_by or first
    # name.
    user = User.objects.get(username=user)
    try:
        profile = UserProfile.objects.get(user=user)
        if profile.call_me_by:
            user = profile.call_me_by
        else:
            user = user.first_name
    except UserProfile.DoesNotExist:
        user = user.first_name
    params['form'] = form
    params['user'] = user
    params['in_or_out'] = in_or_out
    return render_to_response('time.html', params, context_instance=RequestContext(request))


def fail(request):
    """ If signing in or out of a shift fails, show the user a page stating
    that. This is the page shown if someone tries to log in from a non-
    punchclock.
    """
    try:
        message = request.GET['message']
    except:
        pass
    try:
        reason = request.GET['reason']
    except:
        pass
    try:
        log_msg = request.GET['log_msg']
    except:
        pass
    params = {'request': request, 'message': message, 'reason': reason, 'log_msg': log_msg}
    return render_to_response('fail.html', params)


def success(request):
    """ Show a page telling the user what they just successfully did.
    """
    success = request.GET['success']
    at_time = request.GET['at_time']
    location = request.GET['location']
    user = request.GET['user']

    # The following code is used for displaying the user's call_me_by or first
    # name.
    user = User.objects.get(username=user)
    try:
        profile = UserProfile.objects.get(user=user)
        if profile.call_me_by:
            user = profile.call_me_by
        else:
            user = user.first_name
    except UserProfile.DoesNotExist:
        user = user.first_name

    params = {'request': request, 'success': success, 'at_time': at_time, 'location': location, 'user': user}
    return render_to_response('success.html', params, context_instance=RequestContext(request))
