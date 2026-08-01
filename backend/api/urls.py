from django.urls import path

from api.auth import LoginView, LogoutView, SessionView
from api.views.collectables import (
    CollectablesStateView,
    CombineView,
    HarmonyMergeView,
    MergeUpView,
    SellView,
)
from api.views.friends import (
    FriendLinkListCreateView,
    PublicFriendCheckView,
    TrialSessionView,
)
from api.views.health import HealthView
from api.views.rewards import ReceptacleListView, RewardView
from api.views.stats import StatsView
from api.views.tasks import TaskListCreateView
from api.views.treasures import (
    ReceptacleOpenView,
    StateView,
    TreasureBuyView,
    TreasureDiscardView,
    TreasureListView,
)

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("tasks", TaskListCreateView.as_view(), name="tasks"),
    path("stats", StatsView.as_view(), name="stats"),
    path("collectables", CollectablesStateView.as_view(), name="collectables"),
    path("collectables/merge", MergeUpView.as_view(), name="collectables-merge"),
    path("collectables/harmony", HarmonyMergeView.as_view(), name="collectables-harmony"),
    path("collectables/combine", CombineView.as_view(), name="collectables-combine"),
    path("collectables/sell", SellView.as_view(), name="collectables-sell"),
    path("rewards", RewardView.as_view(), name="rewards"),
    path("receptacles", ReceptacleListView.as_view(), name="receptacles"),
    path(
        "receptacles/<str:receptacle_id>/open",
        ReceptacleOpenView.as_view(),
        name="receptacle-open",
    ),
    path("treasures", TreasureListView.as_view(), name="treasures"),
    path("treasures/<str:treasure_id>/buy", TreasureBuyView.as_view(), name="treasure-buy"),
    path(
        "treasures/<str:treasure_id>/discard",
        TreasureDiscardView.as_view(),
        name="treasure-discard",
    ),
    path("state", StateView.as_view(), name="state"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/session", SessionView.as_view(), name="auth-session"),
    path("friends", FriendLinkListCreateView.as_view(), name="friends"),
    path("public/friend/<str:name>", PublicFriendCheckView.as_view(), name="public-friend"),
    path("trial/session", TrialSessionView.as_view(), name="trial-session"),
]
