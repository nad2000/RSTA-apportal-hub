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
from django.forms.widgets import NullBooleanSelect
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


class InlineSubform(LayoutObject):
    # template = "mycollections/formset.html"
    template = "portal/sub_form.html"

    def __init__(self, form_name_in_context, template=None):
        self.formset_name_in_context = form_name_in_context
        self.fields = []
        if template:
            self.template = template

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        form = context[self.formset_name_in_context]
        return render_to_string(self.template, {"form": form})


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
        user = kwargs.get("initial", {}).get("user")

        self.helper = FormHelper(self)
        self.helper.include_media = False

        # self.helper.help_text_inline = True
        # self.helper.html5_required = True
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
                    Div("team_name", TableInlineFormset("members"), css_id="members"),
                ]
            )
        tabs = [
            Tab(
                _("Team" if self.instance.is_team_application else "Applicant"),
                css_id="applicant",
                *fields,
            ),
            Tab(_("Referees"), Div(TableInlineFormset("referees"), css_id="referees"),),
            Tab(
                _("Summary"),
                Field("file", data_toggle="tooltip", title=self.fields["file"].help_text),
                Field("summary"),
            ),
        ]
        if user and not user.is_identity_verified:
            tabs.append(
                Tab(
                    _("Identity Verification"),
                    Field(
                        "photo_identity",
                        data_toggle="tooltip",
                        title=self.fields["photo_identity"].help_text,
                    ),
                    css_id="id-verification",
                ),
            )

        self.helper.layout = Layout(
            TabHolder(*tabs),
            ButtonHolder(
                Submit("save_draft", _("Save Draft"), css_class="btn btn-primary",),
                Submit("submit", _("Submit"), css_class="btn btn-outline-primary",),
                HTML(
                    """
                    <a href="{{ view.get_success_url }}"
                       type="button"
                       role="button"
                       class="btn btn-secondary"
                       id="cancel">
                        %s
                    </a>"""
                    % _("Cancel")
                ),
            ),
        )

    class Meta:
        model = models.Application
        exclude = ["organisation", "state"]
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
        widgets = dict(has_authorized=NullBooleanSelect(attrs=dict(readonly=True)))
        # widgets = dict(has_authorized=forms.CheckboxInput(attrs=dict(readonly=True, disabled=True)))
        # widgets = dict(has_authorized=forms.CheckboxInput(attrs=dict(disabled=True)))
        # widgets = dict(has_authorized=forms.CheckboxInput(attrs=dict(readonly=True)))


MemberFormSet = inlineformset_factory(
    models.Application, models.Member, form=MemberForm, extra=1, can_delete=True
)


class RefereeForm(forms.ModelForm):
    class Meta:
        model = models.Referee
        fields = ["has_testifed", "email", "first_name", "middle_names", "last_name"]
        widgets = dict(has_testifed=NullBooleanSelect(attrs=dict(readonly=True)))


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

    def __init__(self, profile=None, previous_step=None, next_step=None, *args, **kwargs):
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
                self.add_input(
                    Submit(
                        "save",
                        _("Save") if profile.is_completed else _("Finish and Save"),
                        css_class="btn-primary float-right",
                    )
                )
        else:
            # self.add_input(add_more_button)
            self.add_input(Submit("save", _("Save")))
            self.add_input(Button("cancel", _("Cancel"), css_class="btn btn-danger"))


class NominationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        fields = [
            Fieldset(
                _("Nominee"),
                Row(
                    Column("title", css_class="form-group col-1 mb-0"),
                    Column("first_name", css_class="form-group col-3 mb-0"),
                    Column("middle_names", css_class="form-group col-5 mb-0"),
                    Column("last_name", css_class="form-group col-3 mb-0"),
                ),
                "email",
                css_id="nominee",
            ),
            "org",
            "file",
            "summary",
        ]
        self.helper.layout = Layout(
            *fields,
            ButtonHolder(
                Submit("save_draft", _("Save Draft"), css_class="btn btn-primary",),
                Submit("submit", _("Submit"), css_class="btn btn-outline-primary",),
                HTML(
                    """<a href="{{ view.get_success_url }}" class="btn btn-secondary">%s</a>"""
                    % _("Close")
                ),
            ),
        )

    class Meta:
        model = models.Nomination
        fields = [
            "title",
            "first_name",
            "middle_names",
            "last_name",
            "email",
            "org",
            "summary",
            "file",
        ]
        widgets = dict(
            org=autocomplete.ModelSelect2(
                "org-autocomplete",
                attrs={"data-placeholder": _("Choose an organisation or or create a new one ...")},
            ),
            summary=SummernoteInplaceWidget(),
        )


class TestimonyForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        fields = [
            Fieldset(
                _("Testimony"),
                Field("file", data_toggle="tooltip", title=self.fields["file"].help_text),
                Field("summary"),
            ),
        ]
        self.helper.layout = Layout(
            *fields,
            ButtonHolder(
                Submit("save_draft", _("Save Draft"), css_class="btn btn-primary",),
                Submit("submit", _("Submit"), css_class="btn btn-outline-primary",),
                Submit("turn_down", _("I don't wish to Testify"), css_class="btn-outline-danger"),
                HTML(
                    """<a href="{{ view.get_success_url }}" class="btn btn-secondary">%s</a>"""
                    % _("Close")
                ),
            ),
        )

    class Meta:
        model = models.Testimony
        fields = [
            "summary",
            "file",
        ]

        widgets = dict(summary=SummernoteInplaceWidget(),)


class IdentityVerificationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        self.helper.layout = Layout(
            Div(
                HTML(
                    """
                    <embed src="{% url 'identity-verification-file' pk=object.id %}"
                        type="application/pdf"
                        frameBorder="0"
                        scrolling="auto"
                        height="100%"
                        width="100%"
                        style="min-height: 30rem;">
                    </embed>
                    """
                ),
                height="60%",
            ),
            ButtonHolder(
                Submit("accept", _("Accept"), css_class="btn btn-primary",),
                Submit("reject", _("Request Resubmission"), css_class="btn btn-outline-danger",),
                HTML(
                    """
                    <a href="{{ view.get_success_url }}"
                    type="button"
                    role="button"
                    class="btn btn-secondary"
                    id="cancel">
                        %s
                    </a>"""
                    % _("Cancel")
                ),
                css_class="mb-4",
            ),
            Field(
                "resolution",
                data_toggle="tooltip",
                title=_("Please add a comment if you request a resubmission"),
            ),
        )

    class Meta:
        model = models.IdentityVerification
        fields = ["file", "resolution"]
