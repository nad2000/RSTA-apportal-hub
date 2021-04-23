import os
from urllib.parse import parse_qs

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
def person_name(value, with_email=False):

    if hasattr(value, "user"):
        u = value.user
    elif hasattr(value, "submitted_by"):
        u = value.submitted_by
    else:
        u = None

    output = f"{value.title} " if hasattr(value, "title") and value.title else ""
    output += value.first_name or u and u.first_name or ""

    if middle_names := u and u.middle_names or hasattr(value, "middle_names") and value.middle_names or "":
        output = f"{output} {middle_names}"

    output = f"{output} {u and u.last_name or value.last_name or ''}"
    if with_email:
        output = f"{output} ({u and u.email or value.email})"

    if role := hasattr(value, "role") and value.role:
        output = f"{output}, {role}"

    return output


@register.filter()
def person_with_email(value):

    return person_name(value, with_email=True)


@register.filter()
def basename(value):
    return os.path.basename(value) if value else ""


@register.filter()
def all_scores(value, criteria):
    """Get full list of the scores based on the list of the criteria"""
    yield from value.all_scores(criteria)


@register.filter()
def video_id(value):
    """Get full list of the scores based on the list of the criteria"""
    # https://www.youtube.com/watch?v=NsUWXo8M7UA
    # https://youtu.be/NsUWXo8M7UA
    # https://www.youtube.com/embed/NsUWXo8M7UA
    # https://vimeo.com/60803861
    url, *rest = value.split("?")

    if rest and (qs := parse_qs(rest[0])) and "v" in qs:
        return qs["v"][0]
    return url.split("/")[-1]
