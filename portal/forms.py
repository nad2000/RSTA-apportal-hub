from functools import partial

from crispy_forms.bootstrap import Tab, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    TEMPLATE_PACK,
    BaseInput,
    Button,
    ButtonHolder,
    Column,
    Div,
    Field,
    Fieldset,
    Layout,
    LayoutObject,
    Row,
)
from dal import autocomplete
from django import forms
from django.forms import HiddenInput, inlineformset_factory
from django.forms.models import modelformset_factory
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django_select2.forms import ModelSelect2MultipleWidget
from django_summernote.widgets import SummernoteInplaceWidget

from . import models
from .models import Ethnicity, Language, Profile, ProfileCareerStage, Subscription

DateInput = partial(
    forms.DateInput, attrs={"class": "form-control datepicker", "type": "text"}, format="%Y-%m-%d"
)
YearInput = partial(forms.DateInput, attrs={"class": "form-control yearpicker", "type": "text"})
# FileInput = partial(FileInput, attrs={"class": "custom-file-input", "type": "file"})
# FileInput = partial(FileInput, attrs={"class": "custom-file-input"})


class Submit(BaseInput):
    """Submit button."""

    input_type = "submit"

    def __init__(self, *args, **kwargs):
        self.field_classes = "btn" if "css_class" in kwargs else "btn btn-primary"
        super().__init__(*args, **kwargs)


class TableInlineFormset(LayoutObject):
    # template = "mycollections/formset.html"
    template = "portal/table_inline_formset.html"

    def __init__(self, formset_name_in_context, template=None):
        self.formset_name_in_context = formset_name_in_context
        self.fields = []
        if template:
            self.template = template

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        formset = context[self.formset_name_in_context]
        return render_to_string(self.template, {"formset": formset})


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = "__all__"


class UserForm(forms.ModelForm):
    class Meta:
        model = models.User
        fields = ["title", "first_name", "middle_names", "last_name"]


class ProfileForm(forms.ModelForm):
    def clean_is_accepted(self):
        """Allow only 'True'"""
        if not self.cleaned_data["is_accepted"]:
            raise forms.ValidationError("Please read and consent to the Privacy Policy")
        return True

    class Meta:
        model = Profile
        fields = [
            "date_of_birth",
            "gender",
            "ethnicities",
            "education_level",
            "employment_status",
            "primary_language_spoken",
            "iwi_groups",
            "is_accepted",
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
            # protection_pattern_expires_on=DateInput(),
            is_accepted=forms.CheckboxInput(),
        )
        labels = dict(is_accepted="I have read and agree to the <a href='#'>Privacy Policy</a>")


class ApplicationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        fields = [
            Fieldset(
                _(
                    "Team representative"
                    if self.instance.is_team_application
                    else "Individual applicant"
                ),
                Row(
                    Column("title", css_class="form-group col-1 mb-0"),
                    Column("first_name", css_class="form-group col-3 mb-0"),
                    Column("middle_names", css_class="form-group col-5 mb-0"),
                    Column("last_name", css_class="form-group col-3 mb-0"),
                ),
                "email",
                css_id="submitter",
            ),
            Row(Column("position"), Column("org")),
            "postal_address",
            Row(Column("city"), Column("postcode")),
            Row(Column("daytime_phone"), Column("mobile_phone")),
            # ButtonHolder(Submit("submit", "Submit", css_class="button white")),
        ]
        round = (
            models.Round.get(self.initial["round"])
            if "round" in self.initial
            else self.instance.round
        )
        if round.scheme.team_can_apply:
            fields.extend(
                [
                    Field(
                        "is_team_application", data_toggle="toggle", template="portal/toggle.html"
                    ),
                    Div(TableInlineFormset("members"), css_id="members"),
                ]
            )
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    _("Team" if self.instance.is_team_application else "Applicant"),
                    css_id="applicant",
                    *fields
                ),
                Tab(_("Referees"), Div(TableInlineFormset("referees"), css_id="referees"),),
                Tab(_("Summary"), Field("summary")),
            ),
            ButtonHolder(
                Submit(
                    "submit",
                    _("Update" if self.instance.id else "Save"),
                    css_class="btn btn-primary",
                ),
                HTML(
                    """<a href="{{ view.get_success_url }}" class="btn btn-secondary">%s</a>"""
                    % _("Cancel")
                ),
            ),
        )

    class Meta:
        model = models.Application
        exclude = ["organisation"]
        widgets = dict(
            org=autocomplete.ModelSelect2(
                "org-autocomplete",
                attrs={"data-placeholder": _("Choose an organisationor or create a new one ...")},
            ),
            # summary=SummernoteWidget(),
            summary=SummernoteInplaceWidget(),
        )


class MemberForm(forms.ModelForm):

    class Meta:
        model = models.Member
        fields = ["has_authorized", "email", "first_name", "middle_names", "last_name", "role"]
        widgets = dict(has_authorized=forms.CheckboxInput(attrs=dict(readonly=True, disabled=True)))


MemberFormSet = inlineformset_factory(
    models.Application, models.Member, form=MemberForm, extra=1, can_delete=True
)


class RefereeForm(forms.ModelForm):
    class Meta:
        model = models.Referee
        exclude = ["has_testifed", "testified_at", "user"]


RefereeFormSet = inlineformset_factory(
    models.Application, models.Referee, form=RefereeForm, extra=1, can_delete=True
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


class MemberFormSetHelper(FormHelper):

    template = "portal/table_inline_formset.html"

    # def __init__(self, previous_step=None, next_step=None, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     add_more_button = Button(
    #         "add_more", _("Add More"), css_class="btn btn-outline-warning", css_id="add_more"
    #     )
    #     # if previous_step or next_step:
    #     #     previous_button = Button(
    #     #         "previous", "« " + _("Previous"), css_class="btn btn-outline-primary"
    #     #     )
    #     #     previous_button.input_type = "submit"
    #     #     self.add_input(previous_button)
    #     #     self.add_input(add_more_button)
    #     #     if next_step:
    #     #         next_button = Button(
    #     #             "next", _("Next") + " »", css_class="btn btn-primary float-right"
    #     #         )
    #     #         next_button.input_type = "submit"
    #     #         self.add_input(next_button)
    #     #     else:
    #     #         self.add_input(Submit("save", _("Save"), css_class="float-right"))
    #     # else:
    #     #     self.add_input(add_more_button)
    #     #     self.add_input(Submit("save", _("Save")))
    #     #     self.add_input(Button("cancel", _("Cancel"), css_class="btn btn-danger"))
    #     self.add_input(add_more_button)


class ProfileSectionFormSetHelper(FormHelper):

    template = "portal/table_inline_formset.html"

    def __init__(self, previous_step=None, next_step=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # add_more_button = Button(
        #     "add_more", _("Add More"), css_class="btn btn-outline-warning", css_id="add_more"
        # )
        if previous_step or next_step:
            previous_button = Button(
                "previous", "« " + _("Previous"), css_class="btn btn-outline-primary"
            )
            previous_button.input_type = "submit"
            self.add_input(previous_button)
            # self.add_input(add_more_button)
            if next_step:
                next_button = Button(
                    "next", _("Next") + " »", css_class="btn btn-primary float-right"
                )
                next_button.input_type = "submit"
                self.add_input(next_button)
            else:
                self.add_input(Submit("save", _("Save"), css_class="float-right"))
        else:
            # self.add_input(add_more_button)
            self.add_input(Submit("save", _("Save")))
            self.add_input(Button("cancel", _("Cancel"), css_class="btn btn-danger"))
