import os

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
def field_file_name(value, name):
    v = getattr(value, name)
    return v.name if v else None


@register.filter()
def field_file_url(value, name):
    v = getattr(value, name)
    return v.url if v else None


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
def is_file_field(value):
    return isinstance(value, models.FileField)


@register.filter()
def person_with_email(value):

    if hasattr(value, "user"):
        u = value.user
    elif hasattr(value, "submitted_by"):
        u = value.submitted_by
    else:
        u = None
    output = f"{value.title} " if hasattr(value, "title") and value.title else ""
    output += value.first_name or (u.first_name if u else "")

    if (hasattr(value, "middle_names") and value.middle_names) or (u.middle_names if u else ""):
        output += f" {value.middle_names or (u.middle_names if u else '')}"

    output += f" {value.last_name or value.user.last_name} ({value.email or value.user.email})"
    if hasattr(value, "role") and value.role:
        output += f", {value.role}"

    return output


@register.filter()
def basename(value):
    return os.path.basename(value) if value else ""


@register.filter()
def all_scores(value, criteria):
    """Get full list of the scores based on the list of the criteria"""
    scores = {s["criterion_id"]: s for s in value.values()}
    for c in criteria:
        score = scores.get(c.id, {})
        score["criterion"] = c
        yield score
