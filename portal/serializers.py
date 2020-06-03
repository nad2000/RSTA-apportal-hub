from rest_framework import serializers
from . import models


class AffiliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Affiliation
        fields = "__all__"
        # fields = ["username", "email", "name", "url"]

        # extra_kwargs = {"url": {"view_name": "api:user-detail", "lookup_field": "username"}}
