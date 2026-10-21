from django.urls import path

from .api_views.actions import (
    ActivateUserView, ChangeOwnPasswordView, ChangePasswordView, ChangeRoleView, DeactivateUserView,
)
from .api_views.authentication import CurrentUserView, LoginView, LogoutView, RefreshView, VerifyView
from .api_views.security import UserSecurityEventsView, UserSessionsView
from .api_views.user import UserDetailView, UserFilterView, UserListView

app_name = "users"
urlpatterns = [
    path("auth/token/", LoginView.as_view(), name="token-obtain-pair"),
    path("auth/token/refresh/", RefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", VerifyView.as_view(), name="token-verify"),
    path("auth/me/", CurrentUserView.as_view(), name="current-user"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/filter/", UserFilterView.as_view(), name="user-filter"),
    path("users/change-password/", ChangeOwnPasswordView.as_view(), name="change-password"),
    path("users/<uuid:pk>/", UserDetailView.as_view(), name="user-detail"),
    path("users/<uuid:pk>/change-password/", ChangePasswordView.as_view(), name="change-password-user"),
    path("users/<uuid:pk>/change-role/", ChangeRoleView.as_view(), name="change-role"),
    path("users/<uuid:pk>/activate/", ActivateUserView.as_view(), name="user-activate"),
    path("users/<uuid:pk>/deactivate/", DeactivateUserView.as_view(), name="user-deactivate"),
    path("users/<uuid:pk>/sessions/", UserSessionsView.as_view(), name="user-sessions"),
    path("users/<uuid:pk>/security-events/", UserSecurityEventsView.as_view(), name="user-security-events"),
]
