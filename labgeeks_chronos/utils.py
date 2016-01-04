from datetime import datetime, timedelta
import json
from calendar import HTMLCalendar
from datetime import date
import requests
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime
from labgeeks_chronos.models import Shift


def read_api(date, service):
    # request = requests.get("https://depts.washington.edu/hdleads/scheduling/schedman/ws/v1/shift/date")
    # date = whatever day the user chooses, which will be put into the url fro the API; might have to format the date a little to reflect the correct url

    app = settings.SCHEDMAN_API
    app_url = app[service]
    try:
        url = "%s/ws/v1/shift?date=%s" % (app_url, date)
        cert = settings.CERT_FILE
        key = settings.KEY_FILE
        request = requests.get(url, cert=(cert, key))

    except (AttributeError, ValueError) as e:
        url = "%s/ws/v1/%s" % (app_url, date)
        request = requests.get(url)

    return request.json()


def compare(date, service):
    """Given a list of shift of punchclocks, returns shifts where people did not show up and shifts where people clock in/out early/late."""

    raw = read_api(date, service)
    start_date = datetime.strptime(date, '%Y-%m-%d')
    next_date = start_date + timedelta(days=1)

    # TODO: move specific times to settings
    shifts_on_date = Shift.objects.filter(intime__gte=start_date.strftime("%Y-%m-%d 04:00:00"), outtime__lte=next_date.strftime("%Y-%m-%d 03:59:59"))
    no_shows = []
    conflicts = []
    missing_netids = []
    date = datetime.strptime(date, '%Y-%m-%d').date()
    for netid in raw["Shifts"].keys():
        potential_matches = []
        scheduled_shifts = []
        for shift_info in raw["Shifts"][netid]:  # each netid/person might have more than one scheduled shift so we have to iterate through each one before moving onto a new person
            shift = {}
            shift["uwnetid"] = netid
            if shift_info.get("In") == "24:00:00":
                shift["time_in"] = datetime.combine(date + timedelta(days=1), datetime.strptime("00:00:00", "%H:%M:%S").time())
            else:
                shift["time_in"] = datetime.combine(date, datetime.strptime(shift_info.get("In"), "%H:%M:%S").time())
            if shift_info.get("Out") == "24:00:00":
                shift["time_out"] = datetime.combine(next_date, datetime.strptime("00:00:00", "%H:%M:%S").time())
            else:
                if datetime.strptime(shift_info.get("Out"), '%H:%M:%S') < datetime.strptime(shift_info.get("In"), '%H:%M:%S'):
                    shift["time_out"] = datetime.combine(next_date, datetime.strptime(shift_info.get("Out"), "%H:%M:%S").time())
                else:
                    shift["time_out"] = datetime.combine(date, datetime.strptime(shift_info.get("Out"), "%H:%M:%S").time())
            shift["shift_number"] = shift_info.get("Shift")
            scheduled_shifts.append(shift)
        try:
            user = User.objects.get(username=netid)
            response = get_conflicts_and_no_shows(shifts_on_date, user, scheduled_shifts)
            for conflict in response[0]:
                conflicts.append(conflict)
            for no_show in response[1]:
                no_shows.append(no_show)
        except (ValueError, User.DoesNotExist):
            missing_netids.append(netid)

    return (no_shows, conflicts, missing_netids)


def get_conflicts_and_no_shows(shifts_on_date, user, scheduled_shifts):
    conflicts = []
    clean_conflicts = []
    no_show = []
    potential_matches = shifts_on_date.filter(person=user)
    name = user.first_name + " " + user.last_name
    if potential_matches.count() == 0:
        for shift in scheduled_shifts:
            new_no_show = {'In': datetime.strftime(shift['time_in'], '%H:%M:%S'), 'Out': datetime.strftime(shift['time_out'], '%H:%M:%S'), 'Shift': shift['shift_number'], 'netid': shift['uwnetid'], 'name': name}
            no_show.append(new_no_show)
    elif len(scheduled_shifts) > potential_matches.count():
        (matches, no_matches) = get_best_matches(potential_matches, name, scheduled_shifts)
        for match in matches:
            match['name'] = name
            conflicts.append(match)
        for no_match in no_matches:
            no_show.append(no_match)
    else:
        for shift in scheduled_shifts:
            conflict = get_match(potential_matches, shift)
            conflict['name'] = name
            if conflict != "no show":
                conflicts.append(conflict)
            else:
                new_no_show = {'In': datetime.strftime(shift['time_in'], '%H:%M:%S'), 'Out': datetime.strftime(shift['time_out'], '%H:%M:%S'), 'Shift': shift['shift_number'], 'netid': shift['uwnetid'], 'name': name}
                no_show.append(new_no_show)
    for item in conflicts:
        if item is not None:
            clean_conflicts.append(item)

    return (clean_conflicts, no_show)


def get_best_matches(potential_matches, name, scheduled_shifts):
    matches = []
    no_shows = []
    for chron_shift in potential_matches:
        time_diffs = []
        closest_shift = ""
        closest_scheduled_in = datetime.now()
        shortest_diff = timedelta(hours=24)
        chron_in = chron_shift.intime
        for shift in scheduled_shifts:
            scheduled_in_time = shift["time_in"]
            diff = abs(scheduled_in_time - chron_in)
            if diff < shortest_diff:
                shortest_diff = diff
                closest_scheduled_in = scheduled_in_time
                closest_shift = shift
        result = find_tardy(closest_shift, [{"shift": chron_shift, "chron_in": chron_in, "sched_in": closest_scheduled_in}])
        matches.append(result)
        scheduled_shifts.remove(closest_shift)
    # takes care of the rest of the unmatched scheduled shifts
    for no_match in scheduled_shifts:
        new_no_show = {'In': datetime.strftime(no_match['time_in'], '%H:%M:%S'), 'Out': datetime.strftime(no_match['time_out'], '%H:%M:%S'), 'Shift': no_match['shift_number'], 'netid': no_match['uwnetid'], 'name': name}
        no_shows.append(new_no_show)
    return (matches, no_shows)


def get_match(potential_matches, scheduled_shift):
    """Given a list of potential punchclock shifts and a scheduled shift that could be associated with the potential punchclock shifts, will find the correct punchlock shift that matches with the scheduled shift. If none is found, then that means they did not show up for that shift."""
    match = []
    threshold = timedelta(hours=23)
    # For the most part, the in punchclock time closest to the scheduled shift is the best match
    for chron_shift in potential_matches:
        chron_in = chron_shift.intime
        scheduled_in_time = scheduled_shift["time_in"]
        diff = abs(scheduled_in_time - chron_in)
        if diff < threshold:
            # emptys the lists and updates it with a better match
            del match[:]
            match.append({"shift": chron_shift, "chron_in": chron_in, "sched_in": scheduled_in_time})
            threshold = diff

    # Once a match is found, it figures out if that person is late or not.
    if len(match) > 0:
        return find_tardy(scheduled_shift, match)
    else:
        # This line doesn't get hit, ever.
        return "no_show"


def find_tardy(scheduled_shift, match):
    """Given a scheduled shift and the matching punchclock shift, will determine if that person clocked in early/late or clocked out early/late. If it does find an infraction, it will return general information about the shift."""
    details = match[0]
    sched_out = scheduled_shift["time_out"]
    chron_out = details["shift"].outtime

    diff_in = abs(details["chron_in"] - details["sched_in"])
    diff_out = abs(chron_out - sched_out)
    threshold = timedelta(minutes=1)
    shift_in_note = ""
    shift_out_note = ""
    shiftnote = details['shift'].shiftnote
    if '\n\n' in shiftnote:
        split_notes = shiftnote.split('\n\n')
        shift_in_note = split_notes[0]
        shift_out_note = split_notes[1]
    else:
        shift_in_note = shiftnote

    info = {'netid': scheduled_shift['uwnetid'], 'comm_in': shift_in_note, 'comm_out': shift_out_note}

    # figures out if the person clocked in late or early, or clocked out late or early
    if diff_out > threshold:
        info.update({"sched_out": datetime.strftime(scheduled_shift["time_out"], '%H:%M:%S'), "clock_out": datetime.strftime(details["shift"].outtime, '%H:%M:%S'), "sched_in": datetime.strftime(scheduled_shift["time_in"], '%H:%M:%S'), "clock_in": datetime.strftime(details["shift"].intime, '%H:%M:%S')})
        if chron_out < sched_out:
            info.update({"diff_out_early": diff_out})
        else:
            info.update({"diff_out_late": diff_out})
    if diff_in > threshold:
        info.update({"sched_in": datetime.strftime(scheduled_shift['time_in'], '%H:%M:%S'), "clock_in": datetime.strftime(details["shift"].intime, '%H:%M:%S'), "sched_out": datetime.strftime(scheduled_shift["time_out"], '%H:%M:%S'), "clock_out": datetime.strftime(details["shift"].outtime, '%H:%M:%S')})
        if details["chron_in"] < details["sched_in"]:
            info.update({"diff_in_early": diff_in})
        else:
            info.update({"diff_in_late": diff_in})

    return info


def interpret_results(date, service):
    """Given alist of shift of punchclocks, converts the late and missed shifts into something readable and writes it to a file."""
    comp = compare(date, service)
    no_shows = comp[0]
    tardies = comp[1]
    missing_netids = comp[2]
    msg = []
    threshold = timedelta(minutes=5)
    if len(no_shows) > 0:
        for person in no_shows:
            if person["Out"] == "24:00:00":
                person["Out"] = "00:00:00"
            sched_in_temp = datetime.strptime(person['In'], "%H:%M:%S")
            person['In'] = sched_in_temp.strftime("%I:%M %p")

            sched_out_temp = datetime.strptime(person['Out'], "%H:%M:%S")
            person['Out'] = sched_out_temp.strftime("%I:%M %p")

            if 'name' not in person:
                person['name'] = ''

            msg.append({"date": date, "color": "redder", "netid": person['netid'], "change": "", "clock_out": "", "sched_out": person['Out'], "comm_out": "", "clock_in": "", "sched_in": person['In'], "comm_in": "", "status": "No Show", "name": person['name']})

    if len(tardies) > 0:
        for student in tardies:
            if "sched_in" in student:
                sched_in_temp = datetime.strptime(student['sched_in'], "%H:%M:%S")
                student['sched_in'] = sched_in_temp.strftime("%I:%M %p")

                sched_out_temp = datetime.strptime(student['sched_out'], "%H:%M:%S")
                student['sched_out'] = sched_out_temp.strftime("%I:%M %p")

                clock_in_temp = datetime.strptime(student['clock_in'], "%H:%M:%S")
                student['clock_in'] = clock_in_temp.strftime("%I:%M %p")

                clock_out_temp = datetime.strptime(student['clock_out'], "%H:%M:%S")
                student['clock_out'] = clock_out_temp.strftime("%I:%M %p")

            if 'name' not in student:
                student['name'] = ''

            if "diff_in_early" in student:
                if student["diff_in_early"] > threshold:
                    msg.append({"date": date, "color": "oranger", "netid": student['netid'], "change": student['diff_in_early'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock In Early", "name": student['name']})
                else:
                    msg.append({"date": date, "color": "blacker", "netid": student['netid'], "change": student['diff_in_early'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock In Early", "name": student['name']})
            elif "diff_in_late" in student:
                if student["diff_in_late"] > threshold:
                    msg.append({"date": date, "color": "redder", "netid": student['netid'], "change": student['diff_in_late'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock In Late", "name": student['name']})
                else:
                    msg.append({"date": date, "color": "blacker", "netid": student['netid'], "change": student['diff_in_late'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock In Late", "name": student['name']})
            elif "diff_out_early" in student:
                if student["diff_out_early"] > threshold:
                    msg.append({"date": date, "color": "redder", "netid": student['netid'], "change": student['diff_out_early'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock Out Early", "name": student['name']})
                else:
                    msg.append({"date": date, "color": "blacker", "netid": student['netid'], "change": student['diff_out_early'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock Out Early", "name": student['name']})
            elif "diff_out_late" in student:
                if student["diff_out_late"] > threshold:
                    msg.append({"date": date, "color": "oranger", "netid": student['netid'], "change": student['diff_out_late'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock Out Late", "name": student['name']})
                else:
                    msg.append({"date": date, "color": "blacker", "netid": student['netid'], "change": student['diff_out_late'], "clock_out": student['clock_out'], "sched_out": student['sched_out'], "comm_out": student['comm_out'], "clock_in": student['clock_in'], "sched_in": student['sched_in'], "comm_in": student['comm_in'], "status": "Clock Out Late", "name": student['name']})
    return (msg, missing_netids)

class TimesheetCalendar(HTMLCalendar):
    """ This class is used for displaying the timesheet in a calendar format
    """

    def __init__(self, shifts, user=None):
        super(TimesheetCalendar, self).__init__()
        self.shifts = self.group_by_day(shifts)
        self.personal = self.is_personal(shifts)
        if user:
            self.user = user
            #self.can_view_shifts = self.is_staff(request,user)
        else:
            self.user = ''

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if day <= 15:
                cssclass += ' first'
            else:
                cssclass += ' second'
            s = '<strong>%s</strong>' % (day)
            if date.today() == date(self.year, self.month, day):
                cssclass += ' today'
            if day in self.shifts:
                cssclass += ' filled'
                total_hours = 0
                for shift in self.shifts[day]:
                    if shift.outtime:
                        total_hours += float(shift.length())
                body = '<p><a href="/chronos/%s/%s/%s/%s"><i class="icon-list-alt"></i><span class="long">Total Hours: <strong class="hours">' % (self.user.username, self.year, self.month, day) + str(total_hours) + '</strong></span></a></p>'
                s += '%s' % (body)
                return self.day_cell(cssclass, s)
            return self.day_cell(cssclass, s)
        return self.day_cell('noday', '&nbsp;')

    def formatmonth(self, year, month):
        self.year, self.month = year, month
        return super(TimesheetCalendar, self).formatmonth(year, month)

    def group_by_day(self, shifts):
        shifts_by_day = {}
        for shift in shifts:
            if shift.intime.day in shifts_by_day:
                shifts_by_day[shift.intime.day].append(shift)
            else:
                shifts_by_day[shift.intime.day] = [shift]
        return shifts_by_day

    def day_cell(self, cssclass, body):
        return '<td class="%s">%s</td>' % (cssclass, body)

    def is_personal(self, shifts):
        if shifts:
            user = shifts[0].person
            for shift in shifts:
                if shift.person != user:
                    #Calendar is not personal, used for multiple all staff
                    return False
        return True

    def is_staff(self, request, user):
        if request.user.is_staff or request.user == user:
            return True
        return False


class ReportCalendar(TimesheetCalendar):
    """ This class is used for displaying the reports in a monthly calendar
    format.
        Overrides the TimesheetCalendar class by injecting the ability to view
    shifts of a the given day.
    """

    def formatday(self, day, weekday):
        if day != 0:
            cssclass = self.cssclasses[weekday]
            if day <= 15:
                cssclass += ' first'
            else:
                cssclass += ' second'
            s = '<strong>%s</strong>' % (day)
            if date.today() == date(self.year, self.month, day):
                cssclass += ' today'
            if day in self.shifts:
                s += '<p><a href="/chronos/report/%s/%s/%s"><i class="icon-list-alt"></i><span class="long">Shift Details</span></a></p>' % (self.year, self.month, day)

                return super(ReportCalendar, self).day_cell(cssclass, s)
            return super(ReportCalendar, self).day_cell(cssclass, s)
        return super(ReportCalendar, self).day_cell('noday', '&nbsp;')
