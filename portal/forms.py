from functools import partial

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Button, Submit
from dal import autocomplete
from django import forms
from django.forms import HiddenInput
from django.forms.models import modelformset_factory
from django.utils.translation import gettext as _
from django_select2.forms import ModelSelect2MultipleWidget

from . import models
from .models import Ethnicity, Language, Profile, ProfileCareerStage, Subscription

DateInput = partial(
    forms.DateInput, attrs={"class": "form-control datepicker", "type": "text"}, format="%Y-%m-%d"
)
YearInput = partial(forms.DateInput, attrs={"class": "form-control yearpicker", "type": "text"})
# FileInput = partial(FileInput, attrs={"class": "custom-file-input", "type": "file"})
# FileInput = partial(FileInput, attrs={"class": "custom-file-input"})


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
        exclude = [
            "user",
            "career_stages",
            "external_ids",
            "affiliations",
            "is_ethnicities_completed",
            "is_iwi_groups_completed",
            "is_career_stages_completed",
            "is_external_ids_completed",
            "is_employments_completed",
            "is_educations_completed",
            "is_academic_records_completed",
            "is_recognitions_completed",
            "is_cvs_completed",
        ]
        widgets = dict(
            gender=forms.RadioSelect(attrs={"style": "display: inline-block"}),
            date_of_birth=DateInput(),
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


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = models.Application
        exclude = ["organisation"]
        widgets = dict(
            org=autocomplete.ModelSelect2(
                "org-autocomplete",
                attrs={"data-placeholder": _("Choose an organisationor or create a new one ...")},
            )
        )


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
    widgets=dict(profile=HiddenInput(), year_achieved=YearInput(attrs={"min": 1950})),
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

    template = "portal/table_inline_formset.html"

    def __init__(self, previous_step=None, next_step=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_more_button = Button(
            "add_more", _("Add More"), css_class="btn btn-outline-warning", css_id="add_more"
        )
        if previous_step or next_step:
            previous_button = Button(
                "previous", "« " + _("Previous"), css_class="btn btn-outline-primary"
            )
            previous_button.input_type = "submit"
            self.add_input(previous_button)
            self.add_input(add_more_button)
            if next_step:
                next_button = Button(
                    "next", _("Next") + " »", css_class="btn btn-primary float-right"
                )
                next_button.input_type = "submit"
                self.add_input(next_button)
            else:
                self.add_input(Submit("save", _("Save"), css_class="float-right"))
        else:
            self.add_input(add_more_button)
            self.add_input(Submit("save", _("Save")))
            self.add_input(Button("cancel", _("Cancel"), css_class="btn btn-danger"))


class ModelSelect2(autocomplete.ModelSelect2):
    def build_attr(self, attrs):
        attrs = super().build_attrs(attrs)
        attrs["width"] = "null"
        return attrs
