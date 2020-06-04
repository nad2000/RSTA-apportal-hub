from rest_framework import routers, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from . import models, serializers


class AffiliationViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = serializers.AffiliationSerializer
    queryset = models.Affiliation.objects.all()
    lookup_field = "profile"

    def get_queryset(self, *args, **kwargs):
        if self.request.user.profile:
            return self.queryset.filter(profile=self.request.user.profile)
        return models.Affiliation.objects.none()

    @action(detail=False, methods=["GET"])
    def me(self, request):
        serializer = serializers.AffiliationSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)


router = routers.DefaultRouter()
router.register("affiliations", AffiliationViewSet)
