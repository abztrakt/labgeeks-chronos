from django.core.management.base import BaseCommand
from django.core.mail import send_mail
import datetime
from datetime import timedelta
import socket
from optparse import make_option


class Command(BaseCommand):
    args = 'X'
    help = "Gives the url for late report for past X days. Takes number of days (optional, default=7), recipient email(required), service (required) as parameters.\n Usage: labgeeks get_url [-n days] EMAIL SERVICE. Example: labgeeks get_url -n 7 to@example.com ctleads"

    option_list = BaseCommand.option_list + (
        make_option('-n', dest='num', default=7, help='Number of days to generate late report link for.'),)

    def handle(self, *args, **options):
        if len(args) == 2:
            num = int(options['num'])
            end_date = datetime.datetime.now() - timedelta(days=1)
            end_date_display = end_date.strftime("%Y-%m-%d")
            start_date = end_date - timedelta(days=num - 1)
            start_date_display = start_date.strftime("%Y-%m-%d")
            email = args[0]
            service = args[1]

            try:
                HOSTNAME = socket.gethostname()
            except:
                HOSTNAME = 'chaos.s.uw.edu'

            link = "Link for Late Report:  \n http://%s/chronos/report/latetable?start_date=%s&end_date=%s&service=%s" % (HOSTNAME, start_date_display, end_date_display, service)
            subject = "Late Report from %s to %s" % (start_date_display, end_date_display)

            send_mail(subject, link, 'do-not-reply@uw.edu', [email], fail_silently=False)
