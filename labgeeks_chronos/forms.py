from django import forms
from labgeeks_chronos.models import Shift


class DataForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()


class HourForm(forms.Form):
    start_date = forms.DateField()
    end_date = forms.DateField()


class ShiftForm(forms.ModelForm):
    """ The form that submits a sign in / sign out of a shift.
    """
    class Meta:
        model = Shift
        exclude = ('person', 'intime', 'outtime', 'in_clock', 'out_clock')
