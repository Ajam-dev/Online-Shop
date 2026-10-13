from django import forms
from orders.models import Address

class CheckoutForm(forms.Form):
    address = forms.ModelChoiceField(
        queryset=Address.objects.none(),
        label = "آدرس ارسال",
        empty_label="انتخاب آدرس"
    )

    
    def __init__(self, *args, user = None, **kwargs):
        super().__init__(*args, **kwargs)
        
        if user is not None:
            self.fields["address"].queryset = Address.objects.filter(user=user)