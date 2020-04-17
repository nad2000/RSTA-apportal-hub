from django import forms
from django_select2.forms import ModelSelect2MultipleWidget

from .models import Ethnicity, Profile, Subscription


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = "__all__"


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        exclude = ["user"]
        widgets = {
            "ethnicities": ModelSelect2MultipleWidget(
                model=Ethnicity, search_fields=["description__icontains"],
            ),
        }
