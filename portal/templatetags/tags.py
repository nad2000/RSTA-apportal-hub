from django import forms, template
from django.db import models
from django.forms.widgets import NullBooleanSelect
from django.utils.translation import gettext as _

register = template.Library()


@register.filter()
def field_value(value, name):
    """Returns the value of the field of an object."""
    v = getattr(value, name)
    f = value._meta.get_field(name)
    if isinstance(f, models.BooleanField):
        return _("yes") if v else _("no")
    return v


@register.filter()
def fields(value):
    return value._meta.fields


@register.filter()
def disabled_readonly(value):
    attrs = value.field.widget.attrs
    return attrs.get("readonly") and attrs.get("disabled")


@register.filter()
def is_disabled_readonly_checkbox(value):
    attrs = value.field.widget.attrs
    return (
        isinstance(value.field.widget, forms.CheckboxInput)
        and attrs.get("readonly")
        and attrs.get("disabled")
    )


@register.filter()
def is_readonly_nullbooleanfield(value):
    attrs = value.field.widget.attrs
    return isinstance(value.field.widget, NullBooleanSelect) and attrs.get("readonly")


@register.filter()
def member_with_email(value):
    output = value.first_name or value.user.first_name

    if value.middle_names or value.user.middle_names:
        output += f" {value.middle_names or value.user.middle_names}"

    output += f" {value.last_name or value.user.last_name} ({value.email or value.user.email})"
    if value.role:
        output += f", {value.role}"

    return output
