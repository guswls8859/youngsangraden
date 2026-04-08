from django import forms
from .models import Vehicle


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['organization', 'car_number', 'phone', 'start_date', 'end_date', 'note']
        widgets = {
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '소속 입력'}),
            'car_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '예) 12가 3456'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '예) 010-1234-5678'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'note': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '비고 입력 (선택)'}),
        }
        labels = {
            'organization': '소속',
            'car_number': '차량 번호',
            'phone': '핸드폰 번호',
            'start_date': '출입 시작일',
            'end_date': '출입 종료일',
            'note': '비고',
        }
