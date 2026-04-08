from django import forms
from .models import DailyReport, DailyTask


class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = ['report_date', 'issues']
        widgets = {
            'report_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'issues': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '이슈 또는 특이사항을 입력하세요'}),
        }
        labels = {
            'report_date': '보고 날짜',
            'issues': '이슈 및 특이사항',
        }


class DailyTaskForm(forms.ModelForm):
    class Meta:
        model = DailyTask
        fields = ['task_name', 'start_date', 'note']
        widgets = {
            'task_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '업무명 입력'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': '비고 (선택)'}),
        }
        labels = {
            'task_name': '업무명',
            'start_date': '시작일',
            'note': '비고',
        }
