from django import forms 
from payments.models import Gateway

class PaymentForm(forms.Form):
    gateway = forms.ChoiceField(
        choices=Gateway.choices,
        label="انتخاب درگاه پرداخت",
        widget=forms.RadioSelect,
    )
    