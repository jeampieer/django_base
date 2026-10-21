from django.urls import include, path
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView

from core.api.views.health import HealthCheckView, PingView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("health/ping/", PingView.as_view(), name="health-ping"),
    path("api/v1/", include("applications.users.urls", namespace="users")),
    path("api/schema/", SpectacularAPIView.as_view(renderer_classes=[OpenApiJsonRenderer]), name="schema"),
    path("api/v1/example/", include("applications.example.urls", namespace="example")),
]
