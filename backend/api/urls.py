from django.urls import path

from api.views.health import HealthView
from api.views.stats import StatsView
from api.views.tasks import TaskListCreateView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("tasks", TaskListCreateView.as_view(), name="tasks"),
    path("stats", StatsView.as_view(), name="stats"),
]
