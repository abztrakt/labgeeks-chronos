from datetime import datetime, timedelta
import json, requests
from django.conf import settings

def read_api(date):
    #request = requests.get("https://depts.washington.edu/hdleads/scheduling/schedman/ws/v1/shift/date")
    #date = whatever day the user chooses, which will be put into the url fro the API; might have to format the date a little to reflect the correct url

    # eventually hdleads shouldn't be hardcoded here, i set things up so we can loop over 
    # multiple schedman apis
    app = settings.SCHEDMAN_API
    app_url = app['hdleads']
    url= "%s/ws/v1/shift?date=%s" % (app_url, date)

    cert = settings.CERT_FILE
    key = settings.KEY_FILE

    request = requests.get(url, cert=(cert, key))
    return request.json()

def compare(chronos, date):
    """Given a list of shift of punchclocks, returns shifts where people did not show up and shifts where people clock in/out early/late."""

    raw = read_api(date)

    no_shows = []
    conflicts = []

    #for each netid in the scheduler, finds all shifts in chronos that can be potential matches
    for netid in raw["Shifts"].keys():
        for shift in raw["Shifts"][netid]: #each netid/person might have more than one scheduled shift so have to iterate through each one before moving onto a new person
            shift["netid"] = netid
            potential_matches = []
            for i in range(len(chronos)):
                if netid == chronos[i]["netid"]:
                    potential_matches.append(chronos[i])

            #out of all the shifts he/she clocked in, finds the punch clock that matches up with the shift in the scheduler
            if len(potential_matches) == 0:
                no_shows.append(shift)
            else:
                conflict = get_match(potential_matches, shift)
                if conflict != "no show":
                    conflicts.append(conflict)
                else:
                    no_shows.append(shift)

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

    threshold = timedelta(minutes=6)
    info = {"netid": sched_shift["netid"]}

    #figures out if the person clocked in late or early, or clocked out late or early
    if diff_in > threshold:
        info.update({"sched_in": sched_shift["In"], "clock_in": details["shift"]["in"], "comm_in": details["shift"]["comm_in"]})
        if details["chron_in"] < details["sched_in"]:
            info.update({"diff_in_early": diff_in})
            return info
        else:
            info.update({"diff_in_late": diff_in})
            return info
    elif diff_out > threshold:
        info.update({"sched_out": sched_shift["Out"], "clock_out": details["shift"]["out"], "comm_out": details["shift"]["comm_out"]})
        if chron_out < sched_out:
            info.update({"diff_out_early": diff_out})
            return info
        else:
            info.update({"diff_out_late": diff_out})
            return info

def interpet_results(chronos_list, date):
    """Given alist of shift of punchclocks, converts the late and missed shifts into something readable and writes it to a file."""
    comp = compare(chronos_list, date)
    no_shows = comp[0]
    tardies = comp[1]


    msg = []

    if len(no_shows) > 0:
        for person in no_shows:
            msg.append("%s did not show up to his/her shift that started at %s and ended at %s.\n" %(person['netid'], person['In'], person['Out']))

    template = "%s clocked %s %s by %s. He/she clocked %s at %s, when he/she should have clocked %s at %s. He/she did leave this comment: %s.\n"

    if len(tardies) > 0:
        for student in tardies:
            if "diff_in_early" in student:
                msg.append(template %(student['netid'], "in", "early", student['diff_in_early'], "in", student['clock_in'], "in", student['sched_in'], student['comm_in']))
            elif "diff_in_late" in student:
                msg.append(template %(student['netid'], "in", "late", student['diff_in_late'], "in", student['clock_in'], "in", student['sched_in'], student['comm_in']))
            elif "diff_out_early" in student:
                msg.append(template %(student['netid'], "out", "early", student['diff_out_early'], "out", student['clock_out'], "out", student['sched_out'], student['comm_out']))
            elif "diff_out_late" in student:
                msg.append(template %(student['netid'], "out", "late", student['diff_out_late'], "out", student['clock_out'], "out", student['sched_out'], student['comm_out']))
    return msg


