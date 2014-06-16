from datetime import datetime, timedelta
import json
import requests
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime


def read_api(date, service):
    #request = requests.get("https://depts.washington.edu/hdleads/scheduling/schedman/ws/v1/shift/date")
    #date = whatever day the user chooses, which will be put into the url fro the API; might have to format the date a little to reflect the correct url

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


def compare(chronos, date, service):
    """Given a list of shift of punchclocks, returns shifts where people did not show up and shifts where people clock in/out early/late."""

    raw = read_api(date, service)
    no_shows = []
    no_shows_name = []
    conflicts = []
    #for each netid in the scheduler, finds all shifts in chronos that can be potential matches
    for netid in raw["Shifts"].keys():
        for shift in raw["Shifts"][netid]:  # each netid/person might have more than one scheduled shift so have to iterate through each one before moving onto a new person
            shift["netid"] = netid
            potential_matches = []
            for i in range(len(chronos)):
                if netid == chronos[i]["netid"]:
                    potential_matches.append(chronos[i])
                    name = chronos[i]["name"]

            #out of all the shifts he/she clocked in, finds the punch clock that matches up with the shift in the scheduler
            if len(potential_matches) == 0:
                no_shows.append(shift)
                no_shows_name.append(netid)
            else:
                conflict = get_match(potential_matches, shift)
                conflict['name'] = name
                if conflict != "no show":
                    conflicts.append(conflict)
                else:
                    no_shows_name.append(netid)
                    no_shows.append(shift)

    no_shows_objects = User.objects.filter(username__in=no_shows_name)
    for each in no_shows:
        for each_name in no_shows_objects:
            if each['netid'] == each_name.username:
                each['name'] = each_name.get_full_name()
    clean_conflicts = []
    for item in conflicts:
        if item is not None:
            clean_conflicts.append(item)

    return (no_shows, clean_conflicts)


def get_match(potential_matches, sched_shift):
    """Given a list of potential punchclock shifts and a scheduled shift that could be associated with the potential punchclock shifts, will find the correct punchlock shift that matches with the scheduled shift. If none is found, then that means they did not show up for that shift."""
    match = []
    threshold = timedelta(hours=23)
    #For the most part, the in punchclock time closest to the schedueled shift is the best match
    for chron_shift in potential_matches:
        chron_in = datetime.strptime(chron_shift["in"], "%H:%M:%S")
        sched_in = datetime.strptime(sched_shift["In"], "%H:%M:%S")
        diff = abs(sched_in - chron_in)
        if diff < threshold:
            #emptys the lists and updates it with a better match
            del match[:]
            match.append({"shift": chron_shift, "chron_in": chron_in, "sched_in": sched_in})
            threshold = diff

    #Once a match is found, it figures out if that person is late or not.
    if len(match) > 0:
        return find_tardy(sched_shift, match)
    else:
        return "no_show"


def find_tardy(sched_shift, match):
    """Given a scheduled shift and the matching punchclock shift, will determine if that person clocked in early/late or clocked out early/late. If it does find an infraction, it will return general information about the shift."""
    details = match[0]

    #datetime has a problem recognizing 24:00:00, so have to convert to 00:00:00
    if sched_shift["Out"] == "24:00:00":
        sched_shift["Out"] = "00:00:00"

    sched_out = datetime.strptime(sched_shift["Out"], "%H:%M:%S")
    chron_out = datetime.strptime(details["shift"]["out"], "%H:%M:%S")

    diff_in = abs(details["chron_in"] - details["sched_in"])
    diff_out = abs(chron_out - sched_out)

    threshold = timedelta(minutes=1)
    info = {"netid": sched_shift["netid"]}

    #figures out if the person clocked in late or early, or clocked out late or early
    if diff_out > threshold:
        info.update({"sched_out": sched_shift["Out"], "clock_out": details["shift"]["out"], "comm_out": details["shift"]["comm_out"], "sched_in": sched_shift["In"], "clock_in": details["shift"]["in"], "comm_in": details["shift"]["comm_in"]})
        if chron_out < sched_out:
            info.update({"diff_out_early": diff_out})
        else:
            info.update({"diff_out_late": diff_out})
    if diff_in > threshold:
        info.update({"sched_in": sched_shift["In"], "clock_in": details["shift"]["in"], "comm_in": details["shift"]["comm_in"], "sched_out": sched_shift["Out"], "clock_out": details["shift"]["out"], "comm_out": details["shift"]["comm_out"]})
        if details["chron_in"] < details["sched_in"]:
            info.update({"diff_in_early": diff_in})
        else:
            info.update({"diff_in_late": diff_in})

    return info


def interpet_results(chronos_list, date, service):
    """Given alist of shift of punchclocks, converts the late and missed shifts into something readable and writes it to a file."""
    comp = compare(chronos_list, date, service)
    no_shows = comp[0]
    tardies = comp[1]
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

            if not 'name' in person:
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

            if not 'name' in student:
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
    return msg
