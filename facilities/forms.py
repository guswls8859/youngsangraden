from django import forms
from .models import KumnareReport, EoulrimReport, JamjamReport


class KumnareReportForm(forms.ModelForm):
    class Meta:
        model = KumnareReport
        fields = ['report_date', 'sales_amount', 'rental_total_users', 'stamp_issued']
        widgets = {
            'report_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'sales_amount': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
            'rental_total_users': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
            'stamp_issued': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
        }
        labels = {
            'report_date': '보고 날짜',
            'sales_amount': '매출액 (원)',
            'rental_total_users': '렌탈 총이용객 (명)',
            'stamp_issued': '스탬프투어 지급 (개)',
        }


class EoulrimReportForm(forms.ModelForm):
    class Meta:
        model = EoulrimReport
        fields = ['report_date', 'daily_net_sales', 'customer_count', 'notes']
        widgets = {
            'report_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'daily_net_sales': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
            'customer_count': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': '특이사항이 있으면 입력해주세요.'}
            ),
        }
        labels = {
            'report_date': '보고 날짜',
            'daily_net_sales': '당일 순매출 (원)',
            'customer_count': '객수 (명)',
            'notes': '매출증감사유 및 특이사항',
        }


class JamjamReportForm(forms.ModelForm):
    class Meta:
        model = JamjamReport
        fields = ['report_date', 'daily_net_sales', 'customer_count', 'notes']
        widgets = {
            'report_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'daily_net_sales': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
            'customer_count': forms.NumberInput(
                attrs={'class': 'form-control', 'min': 0}
            ),
            'notes': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 3, 'placeholder': '특이사항이 있으면 입력해주세요.'}
            ),
        }
        labels = {
            'report_date': '보고 날짜',
            'daily_net_sales': '당일 순매출 (원)',
            'customer_count': '객수 (명)',
            'notes': '매출증감사유 및 특이사항',
        }
