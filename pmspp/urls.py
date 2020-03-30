from django.urls import path

from .views import index, test_task

urlpatterns = [
    # path('<int:pk>', ProductDetailView.as_view(), name="product-detail"),
    path("", index, name="home"),
    path("test_task/<message>", test_task),
    # path('', ProductListView.as_view(), name="product-list"),
]
