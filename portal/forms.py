import datetime
import os
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
from django.forms import HiddenInput, Widget, inlineformset_factory
from django.forms.models import BaseInlineFormSet, modelformset_factory
from django.forms.widgets import NullBooleanSelect, TextInput
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django_summernote.widgets import SummernoteInplaceWidget

from . import models

DateInput = partial(
    forms.DateInput,
    attrs={
        "class": "form-control datepicker",
        "type": "text",
        "data-date-end-date": datetime.date.today().isoformat(),
    },
    format="%Y-%m-%d",
)


YearInput = partial(forms.DateInput, attrs={"class": "form-control yearpicker", "type": "text"})
# FileInput = partial(FileInput, attrs={"class": "custom-file-input", "type": "file"})
# FileInput = partial(FileInput, attrs={"class": "custom-file-input"})


class OppositeBooleanField(forms.BooleanField):
    def prepare_value(self, value):
        return not value  # toggle the value when loaded from the model

    def to_python(self, value):
        value = super(OppositeBooleanField, self).to_python(value)
        return not value  # toggle the incoming value from form submission


class Submit(BaseInput):
    """Submit button."""

    input_type = "submit"

    def __init__(self, *args, **kwargs):
        self.field_classes = "btn" if "css_class" in kwargs else "btn btn-primary"
        super().__init__(*args, **kwargs)
        self.attrs.update(kwargs)


class TelInput(TextInput):
    input_type = "tel"


class TableInlineFormset(LayoutObject):
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
        self.subform_name_in_context = form_name_in_context
        self.fields = []
        if template:
            self.template = template

    def render(self, form, form_style, context, template_pack=TEMPLATE_PACK):
        form = context[self.subform_name_in_context]
        return render_to_string(self.template, {"form": form})


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = models.Subscription
        fields = "__all__"


class UserForm(forms.ModelForm):
    class Meta:
        model = models.User
        fields = ["title", "first_name", "middle_names", "last_name"]


class ProfileForm(forms.ModelForm):
    def clean_is_accepted(self):
        """Allow only 'True'"""
        if not self.cleaned_data["is_accepted"]:
            raise forms.ValidationError(_("Please read and consent to the Privacy Policy"))
        return True

    class Meta:
        model = models.Profile
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
            ethnicities=autocomplete.ModelSelect2Multiple(url="ethnicity-autocomplete"),
            # ethnicities=ModelSelect2MultipleWidget(
            #     model=models.Ethnicity,
            #     search_fields=["description__icontains"],
            # ),
            sex=forms.RadioSelect,
            # languages_spoken=ModelSelect2MultipleWidget(
            #     model=models.Language,
            #     search_fields=["description__icontains"],
            # ),
            # iwi_groups=ModelSelect2MultipleWidget(
            #     model=models.IwiGroup,
            #     search_fields=["description__icontains"],
            # ),
            iwi_groups=autocomplete.ModelSelect2Multiple(url="iwi-group-autocomplete"),
            # protection_pattern_expires_on=DateInput(),
            is_accepted=forms.CheckboxInput(),
        )
        labels = dict(
            is_accepted=gettext_lazy(
                "I have read and agreed to the "
                "<a href='#' data-toggle='modal' data-target='#privacy-statement'>Privacy Statement</a>"
            )
        )


class ApplicationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        initial = kwargs.get("initial", {})
        user = initial.get("user")
        # language = initial.get("language", "en")

        self.helper = FormHelper(self)
        instance = self.instance
        # self.helper.help_text_inline = True
        # self.helper.html5_required = True

        fields = [
            Fieldset(
                _("Team representative")
                if instance and instance.is_team_application
                else _("Individual applicant"),
                Row(
                    Column("title", css_class="form-group col-2 mb-0"),
                    Column("first_name", css_class="form-group col-3 mb-0"),
                    Column("middle_names", css_class="form-group col-4 mb-0"),
                    Column("last_name", css_class="form-group col-3 mb-0"),
                ),
                "email",
                css_id="submitter",
            ),
            Row(
                Column("org", css_class="col-9"),
                Column("position", css_class="col-3"),
            ),
            "postal_address",
            Row(Column("city"), Column("postcode")),
            # Row(Column("daytime_phone"), Column("mobile_phone")),
            Row(
                Column(
                    Field(
                        "daytime_phone",
                        pattern=r"\+?[0-9- ]+",
                        placeholder="e.g., +64 4 472 7421",
                    )
                ),
                Column(
                    Field(
                        "mobile_phone",
                        pattern=r"\+?[0-9-]+",
                        placeholder="e.g., +64 4 472 7421",
                    )
                ),
            ),
            # ButtonHolder(Submit("submit", "Submit", css_class="button white")),
        ]
        if instance.submitted_by and not instance.submitted_by == user:
            fields.append(Field("is_tac_accepted", type="hidden"))

        round = (
            models.Round.get(self.initial["round"]) if "round" in self.initial else instance.round
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

        if round.application_template:
            help_text = _(
                'You can download the application form template at <strong><a href="%s">%s</a></strong>'
            ) % (round.application_template.url, os.path.basename(round.application_template.name))
            self.fields["file"].help_text = help_text
            summary_fields = [
                # HTML(f'<div class="alert alert-info" role="alert">{help_text}</div>'),
                Field("file"),
            ]
        else:
            summary_fields = [
                Field("file", data_toggle="tooltip", title=self.fields["file"].help_text),
            ]

        if round.budget_template and not (
            instance and instance.submitted_by and instance.submitted_by != user
        ):
            help_text = _(
                'You can download the budget template at <strong><a href="%s">%s</a></strong>'
            ) % (round.budget_template.url, os.path.basename(round.budget_template.name))
            # fields.append(HTML(f'<div class="alert alert-info" role="alert">{help_text}</div>'))
            summary_fields.append(Field("budget"))
            self.fields["budget"].help_text = help_text

        # if round.scheme.research_summary_required:
        #     summary_fields.extend(
        #         [
        #             Field(
        #                 "is_bilingual_summary", data_toggle="toggle", template="portal/toggle.html"
        #             ),
        #             Row(Field("summary"), Field(f"summary_{'en' if language=='mi' else 'mi'}")),
        #         ]
        #     )
        if round.scheme.presentation_required:
            self.fields["presentation_url"].required = True
            summary_fields.insert(
                0,
                Field(
                    "presentation_url",
                    data_toggle="tooltip",
                    title=self.fields["presentation_url"].help_text,
                ),
            )
        tabs = [
            Tab(
                _("Team") if self.instance.is_team_application else _("Applicant"),
                css_id="applicant",
                *fields,
            ),
            Tab(
                _("Referees"),
                Div(TableInlineFormset("referees"), css_id="referees"),
            ),
            Tab(
                _("Summary and Forms"),
                css_id="summary",
                *summary_fields,
            ),
        ]
        # if user and not user.is_identity_verified:
        if (
            round.pid_required
            and not user.is_identity_verified
            and (
                not (instance and instance.id)
                or (not instance.submitted_by_id or instance.submitted_by == user)
            )
        ):
            tabs.append(
                Tab(
                    _("Identity Verification"),
                    InlineSubform("identity_verification"),
                    css_id="id-verification",
                ),
            )

        if round.ethics_statement_required:
            tabs.append(
                Tab(
                    _("Ethics"),
                    InlineSubform("ethics_statement"),
                    css_id="ethics-statement",
                ),
            )

        if not instance.submitted_by or instance.submitted_by == user:
            tac_text = _(
                "As authorized lead applicant, I affirm that all information provided in this application is "
                "to the best of my knowledge true and correct. "
                "<br/><br/>I affirm that if successful, I (and where relevant, my team) will participate in publicity "
                "and that the content of this application can be used in promotion of the Prizes."
                "<br/><br/>If the Prize comes with conditions on use, I affirm that any Prize money will be used in "
                "accordance with the Prize's guidelines, and in accord with any plan submitted as part "
                "of the Prize application"
            )
            tabs.append(
                Tab(
                    _("Terms and Conditions"),
                    HTML(f'<div class="alert alert-dark" role="alert">{tac_text}</div>'),
                    Field("is_tac_accepted"),
                    css_id="tac",
                ),
            )

        submission_disabled = (
            not instance.is_tac_accepted
            and instance.submitted_by
            and instance.submitted_by != user
        )
        submit_button = Submit(
            "submit",
            _("Submit"),
            # disabled=not instance.is_tac_accepted,  # and instance.submitted_by != user,
            data_toggle="tooltip",
            title=_(
                "Your team leader must accept the Terms and Conditions before the submission can happen"
            )
            if submission_disabled
            else _("Submit the application"),
            css_class="btn-outline-primary",
            disabled=submission_disabled,
        )
        self.helper.layout = Layout(
            TabHolder(*tabs),
            ButtonHolder(
                Button("previous", "« " + _("Previous"), css_class="btn-outline-primary"),
                Div(
                    Submit(
                        "save_draft",
                        _("Save"),
                        css_class="btn-primary",
                        data_toggle="tooltip",
                        title=_("Save draft application"),
                    ),
                    submit_button,
                    HTML(
                        """<a href="{{ view.get_success_url }}"
                        type="button"
                        role="button"
                        class="btn btn-secondary"
                        id="cancel">
                            %s
                        </a>"""
                        % _("Cancel")
                    ),
                    Button("next", _("Next") + " »", css_class="btn-primary"),
                    css_class="float-right",
                ),
                css_class="mb-5",
            ),
        )
        self.helper.include_media = False

    class Meta:
        model = models.Application
        exclude = [
            "organisation",
            "state",
            "round",
            "submitted_by",
            "converted_file",
            "cv",
        ]
        widgets = dict(
            org=autocomplete.ModelSelect2(
                "org-autocomplete",
                attrs={"data-placeholder": _("Choose an organisation or create a new one ...")},
            ),
            # summary=SummernoteWidget(),
            daytime_phone=TelInput(),
            mobile_phone=TelInput(),
            # summary=SummernoteInplaceWidget(),
            # summary_en=SummernoteInplaceWidget(),
            # summary_mi=SummernoteInplaceWidget(),
            ethics_statement__comment=SummernoteInplaceWidget(),
            # round=HiddenInput(),
        )


class InvitationStatusInput(Widget):

    template_name = "portal/widgets/invitation_status.html"


class MemberForm(forms.ModelForm):
    class Meta:
        model = models.Member
        fields = ["status", "email", "first_name", "middle_names", "last_name", "role"]
        widgets = dict(
            has_authorized=NullBooleanSelect(attrs=dict(readonly=True)),
            status=InvitationStatusInput(attrs={"readonly": True}),
        )


MemberFormSet = inlineformset_factory(
    models.Application, models.Member, form=MemberForm, extra=1, can_delete=True
)


class RefereeForm(forms.ModelForm):
    class Meta:
        model = models.Referee
        fields = ["status", "email", "first_name", "middle_names", "last_name"]
        widgets = dict(
            has_testifed=NullBooleanSelect(attrs=dict(readonly=True)),
            status=InvitationStatusInput(attrs={"readonly": True}),
        )


class MandatoryApplicationFormInlineFormSet(BaseInlineFormSet):
    def clean(self):
        pass


RefereeFormSet = inlineformset_factory(
    models.Application,
    models.Referee,
    form=RefereeForm,
    formset=MandatoryApplicationFormInlineFormSet,
    extra=1,
    can_delete=True,
)


class ProfileCareerStageForm(forms.ModelForm):
    class Meta:
        exclude = ()
        model = models.ProfileCareerStage


ProfileCareerStageFormSet = modelformset_factory(
    models.ProfileCareerStage,
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


class ProfilePersonIdentifierForm(forms.ModelForm):
    def clean(self):
        data = super().clean()
        if getattr(data.get("code"), "code") == "02":
            p = data.get("profile")
            u = p.user
            orcid = data["value"]
            if (
                not u.orcid.endswith(orcid)
                or not u.socialaccount_set.all().filter(provider="orcid", uid=orcid).exists()
            ):
                raise forms.ValidationError(
                    _(
                        "Invalid ORCID iD value: %(value)s. "
                        "The ID should be authenticated either by linking your account to ORCID or TUAKIRI"
                    ),
                    code="invalid",
                    params={"value": orcid},
                )

        return data

    class Meta:
        exclude = ()
        model = models.ProfilePersonIdentifier


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
                "previous", "« " + _("Previous"), css_class="btn-outline-primary"
            )
            previous_button.input_type = "submit"
            self.add_input(previous_button)
            complete_button = Button(
                "complete",
                _("Complete"),
                data_toggle="tooltip",
                title=_("Skip the rest of the profile sections and complete the profile now"),
                css_class="btn-outline-secondary",
            )
            complete_button.input_type = "submit"
            self.add_input(complete_button)
            # self.add_input(add_more_button)
            if next_step:
                next_button = Button("next", _("Next") + " »", css_class="btn-primary float-right")
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
            self.add_input(Button("cancel", _("Cancel"), css_class="btn-danger"))


class NominationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        r = kwargs["initial"].get("round") or self.instance.round

        self.helper = FormHelper(self)
        self.helper.include_media = False
        self.helper.form_id = "nomination-form"
        fields = [
            "round",
            "nominator",
            Fieldset(
                _("Nominee"),
                Row(
                    Column("title", css_class="form-group col-2 mb-0"),
                    Column("first_name", css_class="form-group col-3 mb-0"),
                    Column("middle_names", css_class="form-group col-4 mb-0"),
                    Column("last_name", css_class="form-group col-3 mb-0"),
                ),
                "email",
                css_id="nominee",
            ),
            "org",
        ]
        if r and r.nomination_template:
            help_text = _(
                'You can download the nomination form template at <strong><a href="%s">%s</a></strong>'
            ) % (r.nomination_template.url, os.path.basename(r.nomination_template.name))
            # fields.append(HTML(f'<div class="alert alert-info" role="alert">{help_text}</div>'))
            fields.append(Field("file", label=help_text, help_text=help_text))
            self.fields["file"].help_text = help_text
        else:
            fields.append("file")

        # fields.append("summary")
        was_submitted = self.instance and self.instance.id and self.instance.status == "submitted"
        self.helper.layout = Layout(
            *fields,
            HTML("""<input type="hidden" name="action">"""),
            ButtonHolder(
                Submit(
                    "save_draft",
                    _("Save"),
                    css_class="btn-primary",
                    data_toggle="tooltip",
                    disabled=was_submitted,
                    title=_("Nomination was already submitted")
                    if was_submitted
                    else _("Save draft nomination"),
                ),
                Button(
                    "submit_button",
                    _("Re-submit") if was_submitted else _("Submit"),
                    css_class="btn-outline-primary",
                    # data_toggle="modal",
                    # data_target="#confirm-submit",
                ),
                HTML(
                    """<a href="{{ view.get_success_url }}" class="btn btn-secondary">%s</a>"""
                    % _("Close")
                ),
                css_class="mb-4 float-right",
            ),
        )

    class Meta:
        model = models.Nomination
        fields = [
            "round",
            "nominator",
            "title",
            "first_name",
            "middle_names",
            "last_name",
            "email",
            "org",
            # "summary",
            "file",
        ]
        widgets = dict(
            org=autocomplete.ModelSelect2(
                "org-autocomplete",
                attrs={"data-placeholder": _("Choose an organisation or create a new one ...")},
            ),
            nominator=HiddenInput(),
            round=HiddenInput(),
            # summary=SummernoteInplaceWidget(),
        )


class TestimonialForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        self.helper.form_id = "entry-form"
        round = self.instance.application.round
        fields = [
            Field("file", data_toggle="tooltip", title=self.fields["file"].help_text),
            # Field("summary"),
            # Field("referee"),
        ]
        if round.referee_template:
            help_text = _(
                'You can download the application review form template at <strong><a href="%s">%s</a></strong>'
            ) % (round.referee_template.url, os.path.basename(round.referee_template.name))
            # fields.insert(0, HTML(f'<div class="alert alert-info" role="alert">{help_text}</div>'))
            self.fields["file"].help_text = help_text
        fields = [
            Fieldset(_("Testimonial"), *fields),
        ]

        self.helper.layout = Layout(
            *fields,
            HTML("""<input type="hidden" name="action">"""),
            ButtonHolder(
                Submit(
                    "save_draft",
                    _("Save"),
                    css_class="btn-primary",
                    data_toggle="tooltip",
                    title=_("Save draft testimonial"),
                ),
                Button(
                    "submit_button",
                    _("Submit"),
                    css_class="btn-outline-primary",
                ),
                Submit(
                    "turn_down",
                    _("I do not wish to provide a testimonial"),
                    css_class="btn-outline-danger",
                ),
                HTML(
                    """<a href="{{ view.get_success_url }}" class="btn btn-secondary">%s</a>"""
                    % _("Close")
                ),
                css_class="mb-4 float-right",
            ),
        )

    class Meta:
        model = models.Testimonial
        fields = [
            # "summary",
            "file",
        ]

        # widgets = dict(
        #     summary=SummernoteInplaceWidget(),
        # )


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
                Submit(
                    "accept",
                    _("Accept"),
                    css_class="btn-primary",
                ),
                Submit(
                    "reject",
                    _("Request resubmission"),
                    css_class="btn-outline-danger",
                ),
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
                css_class="mb-4 float-right",
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


class PanellistForm(forms.ModelForm):
    class Meta:
        model = models.Panellist
        exclude = ()
        widgets = dict(
            has_authorized=NullBooleanSelect(attrs=dict(readonly=True)),
            status=InvitationStatusInput(attrs={"readonly": True}),
            round=HiddenInput(),
        )


PanellistFormSet = modelformset_factory(
    models.Panellist,
    form=PanellistForm,
    exclude=(),
    can_delete=True,
    widgets={"round": HiddenInput(), "status": InvitationStatusInput(attrs={"readonly": True})},
)


class PanellistFormSetHelper(FormHelper):
    template = "portal/table_inline_formset.html"

    def __init__(self, panellist=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_input(
            Submit(
                "send_invite",
                _("Invite"),
                css_class="btn-primary",
            )
        )
        self.add_input(Submit("cancel", _("Cancel"), css_class="btn-danger"))


class ConflictOfInterestForm(forms.ModelForm):

    has_conflict = OppositeBooleanField(label=_("Conflict of Interest"), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        fields = [
            Field(
                "has_conflict",
                data_toggle="toggle",
                template="portal/toggle.html",
                data_on=_("No"),
                data_off=_("Yes"),
                data_onstyle="success",
                data_offstyle="danger",
            ),
            Field("comment"),
        ]
        self.helper.layout = Layout(
            *fields,
            ButtonHolder(
                Submit(
                    "submit",
                    _("Submit"),
                    css_class="btn-outline-primary",
                ),
                HTML(
                    """<a href="{{ view.get_success_url }}" class="btn btn-secondary">%s</a>"""
                    % _("Close")
                ),
                css_class="mb-4 float-right",
            ),
        )

    class Meta:
        model = models.ConflictOfInterest
        fields = [
            "comment",
            "has_conflict",
        ]

        widgets = dict(comment=SummernoteInplaceWidget())


class CriterionWidget(Widget):
    # input_type = 'radio'
    template_name = "portal/widgets/criterion.html"
    # option_template_name = 'django/forms/widgets/radio_option.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value:
            context["value_label"] = self.choices.queryset.filter(id=value).first().definition
        return context


class ReadOnlyApplicationWidget(Widget):
    # input_type = 'radio'
    template_name = "portal/widgets/application.html"
    # option_template_name = 'django/forms/widgets/radio_option.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value:
            context["object"] = (
                self.choices.queryset.select_related("round").filter(id=value).first()
            )
        return context


class ScoreForm(forms.ModelForm):

    value = forms.TypedChoiceField(choices=zip(range(1, 10), range(1, 10)))

    def __init__(self, *args, **kwargs):
        self.value = forms.TypedChoiceField(choices=range(10))
        super().__init__(*args, **kwargs)

        self.helper = FormHelper(self)
        self.helper.include_media = False
        self.helper.form_tag = False
        fields = [
            Field("criterion"),
            Field("value"),
        ]
        criterion = (
            self.instance.criterion
            if hasattr(self.instance, "criterion")
            else self.initial.get("criterion")
        )
        if criterion:
            self.fields["comment"].required = criterion.comment
            self.comment_required = criterion.comment
            if criterion.comment:
                fields.append(Field("comment", required=True))
            else:
                fields.append(Field("comment"))
        self.fields["comment"].widget.attrs = {"rows": 3}
        self.fields["value"] = forms.TypedChoiceField(
            choices=zip(
                range(criterion.min_score, criterion.max_score + 1),
                range(criterion.min_score, criterion.max_score + 1),
            )
            if criterion
            else zip(range(11), range(11))
        )
        self.helper.layout = Layout(*fields)

    class Meta:
        model = models.Score
        fields = [
            "criterion",
            "value",
            "comment",
        ]
        widgets = dict(
            criterion=CriterionWidget(),
        )


class ThreeValuedBooleanField(forms.BooleanField):
    def to_python(self, value):
        """Return a Python boolean object."""
        if value is None or (isinstance(value, str) and value.lower() in ["null", "none", "nil"]):
            return None
        if isinstance(value, str) and value.lower() in ("false", "0"):
            value = False
        else:
            value = bool(value)
        return super().to_python(value)


class RoundConflictOfInterestForm(forms.ModelForm):

    has_conflict = ThreeValuedBooleanField(
        label=_("Conflict of Interest"), required=False, widget=forms.HiddenInput()
    )
    # has_conflict = forms.BooleanField(label=_("Conflict of Interest"), required=False)
    # has_conflict = forms.HiddenInput()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # instance = getattr(self, "instance", None)
        # if instance and instance.id:
        #     self.fields["application"]

        self.fields["comment"].widget.attrs = {"rows": 3}

        self.helper = FormHelper(self)
        self.helper.include_media = False
        fields = [
            "application",
            "has_conflict",
            # Field(
            #     "has_conflict",
            #     data_toggle="toggle",
            #     template="portal/toggle.html",
            #     data_on=_("Yes"),
            #     data_off=_("No"),
            #     data_onstyle="danger",
            #     data_offstyle="success",
            # ),
            "comment",
            # Field("comment"),
        ]
        self.helper.layout = Layout(
            *fields,
        )


class ScoreSheetForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):

        self.helper = FormHelper()
        super().__init__(*args, **kwargs)

        instance = kwargs.get("instance")
        r = instance and instance.round or kwargs["initial"].get("round")

        fields = [
            "file",
            Submit(
                "submit", _("Upload the Score Sheet"), css_class="btn-primary mb-5 float-right"
            ),
        ]
        if r.score_sheet_template:
            help_text = _(
                'You can download the round score sheet template at <strong><a href="%s">%s</a></strong>'
            ) % (r.score_sheet_template.url, os.path.basename(r.score_sheet_template.name))
            # fields.append(HTML(f'<div class="alert alert-info" role="alert">{help_text}</div>'))
            self.fields["file"].help_text = help_text

        self.helper.add_layout(Layout(*fields))

    class Meta:
        model = models.ScoreSheet
        fields = ["file"]
