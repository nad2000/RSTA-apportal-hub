from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit
from django import forms
from django.forms.models import modelformset_factory
from django_select2.forms import ModelSelect2MultipleWidget

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
        exclude = ["user"]
        widgets = dict(
            ethnicities=ModelSelect2MultipleWidget(
                model=Ethnicity, search_fields=["description__icontains"],
            ),
            sex=forms.RadioSelect,
            languages_spoken=ModelSelect2MultipleWidget(
                model=Language, search_fields=["description__icontains"],
            ),
            is_acceted=forms.CheckboxInput(),
        )
        labels = dict(is_accepted="I have read and agree to the <a href='#'>Privacy Policy</a>")


class ProfileCareerStageForm(forms.ModelForm):
    class Meta:
        model = ProfileCareerStage
        exclude = ["profile"]

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     self.helper = FormHelper()
    #     self.helper.layout = Layout(
    #         Row(
    #             Column("year_achieved", css_class="form-group col-md-6 mb-0"),
    #             Column("career_stage", css_class="form-group col-md-6 mb-0"),
    #             css_class="form-row",
    #         ),
    #         # "address_1",
    #         # "address_2",
    #         # Row(
    #         #     Column("city", css_class="form-group col-md-6 mb-0"),
    #         #     Column("state", css_class="form-group col-md-4 mb-0"),
    #         #     Column("zip_code", css_class="form-group col-md-2 mb-0"),
    #         #     css_class="form-row",
    #         # ),
    #         # "check_me_out",
    #         # Submit("submit", "Sign in"),
    #     )


ProfileCareerStageFormSet = modelformset_factory(
    ProfileCareerStage,
    form=ProfileCareerStageForm,
    # exclude=["profile"],
    # fields=['name', 'language'],
    # extra=1,
    can_delete=True,
)


class ProfileCareerStageFormSetHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.layout = Layout(
            Row(
                Column("year_achieved", css_class="form-group col-md-4 mb-0"),
                Column("career_stage", css_class="form-group col-md-8 mb-0"),
                css_class="form-row",
            ),
        )
        self.template = "bootstrap4/table_inline_formset.html"
