from django.urls import path

from api.views.collectables import (
    CollectablesStateView,
    CombineView,
    HarmonyMergeView,
    MergeUpView,
    SellView,
)
from api.views.health import HealthView
from api.views.stats import StatsView
from api.views.tasks import TaskListCreateView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("tasks", TaskListCreateView.as_view(), name="tasks"),
    path("stats", StatsView.as_view(), name="stats"),
    path("collectables", CollectablesStateView.as_view(), name="collectables"),
    path("collectables/merge", MergeUpView.as_view(), name="collectables-merge"),
    path("collectables/harmony", HarmonyMergeView.as_view(), name="collectables-harmony"),
    path("collectables/combine", CombineView.as_view(), name="collectables-combine"),
    path("collectables/sell", SellView.as_view(), name="collectables-sell"),
]
