from django import forms
from .models import InfoReport


class InfoReportForm(forms.ModelForm):
    class Meta:
        model = InfoReport
        fields = [
            'report_date',
            'shuttle_total',
            'info_note',
            'patrol_note',
        ]
        widgets = {
            'report_date':   forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'shuttle_total': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'info_note':     forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'patrol_note':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
