from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from django import forms
from django.forms import HiddenInput, NumberInput
from django.forms.models import modelformset_factory
from django_select2.forms import ModelSelect2MultipleWidget

from . import models
from .models import Ethnicity, Language, Profile, ProfileCareerStage, Subscription


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = "__all__"


class ProfileForm(forms.ModelForm):
    def clean_is_accepted(self):
        """Allow only 'True'"""
        if not self.cleaned_data["is_accepted"]:
            raise forms.ValidationError("Please read and consent to the Privacy Policy")
        return True

    class Meta:
        model = Profile
        exclude = ["user", "career_stages", "external_ids"]
        widgets = dict(
            ethnicities=ModelSelect2MultipleWidget(
                model=Ethnicity, search_fields=["description__icontains"],
            ),
            sex=forms.RadioSelect,
            languages_spoken=ModelSelect2MultipleWidget(
                model=Language, search_fields=["description__icontains"],
            ),
            iwi_groups=ModelSelect2MultipleWidget(
                model=models.IwiGroup, search_fields=["description__icontains"],
            ),
            is_acceted=forms.CheckboxInput(),
        )
        labels = dict(is_accepted="I have read and agree to the <a href='#'>Privacy Policy</a>")


class ProfileCareerStageForm(forms.ModelForm):
    class Meta:
        exclude = ()
        model = ProfileCareerStage


ProfileCareerStageFormSet = modelformset_factory(
    ProfileCareerStage,
    # form=ProfileCareerStageForm,
    # fields=["profile", "year_achieved", "career_stage"],
    exclude=(),
    can_delete=True,
    widgets=dict(profile=HiddenInput(), year_achieved=NumberInput(attrs={"min": 1950})),
)


ProfilePersonIdentifierFormSet = modelformset_factory(
    models.ProfilePersonIdentifier,
    # form=ProfileCareerStageForm,
    # fields=["profile", "year_achieved", "career_stage"],
    exclude=(),
    can_delete=True,
    widgets=dict(profile=HiddenInput()),
)


class ProfileSectionFormSetHelper(FormHelper):

    template = "bootstrap4/table_inline_formset.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_input(Submit("save", "Save"))
        self.add_input(Button("cancel", "Cancel", css_class="btn btn-danger"))
