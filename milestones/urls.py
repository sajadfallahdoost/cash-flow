from django.urls import path
from .views import milestones_list_create, milestones_rud

urlpatterns = [
    path("milestones/", milestones_list_create, name="milestones-list-create"),
    path("milestones/<int:pk>/", milestones_rud, name="milestones-rud"),
]
