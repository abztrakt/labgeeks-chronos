from django import forms
from labgeeks_chronos.models import Shift
from django.conf import settings


class DataForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()


class LateForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField(required=False)
    service_choices = tuple(settings.SCHEDMAN_API.keys())
    z = []
    for i in service_choices:
        z.insert(0, (i, i))
    service_choices = z
    service = forms.ChoiceField(widget=forms.Select, choices=service_choices)


class HourForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()


class ShiftForm(forms.ModelForm):
    """ The form that submits a sign in / sign out of a shift.
    """
    class Meta:
        model = Shift
        exclude = ('person', 'intime', 'outtime', 'in_clock', 'out_clock')
