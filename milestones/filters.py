import django_filters as df
from commons.filters import DateFromToFilter
from .models import Milestone

class MilestoneFilter(DateFromToFilter):
    project = df.NumberFilter(field_name="project_id", lookup_expr="exact")
    status  = df.CharFilter(field_name="status", lookup_expr="iexact")
    due_from = df.DateFilter(field_name="due_date", lookup_expr="gte")
    due_to   = df.DateFilter(field_name="due_date", lookup_expr="lte")
    planned_min = df.NumberFilter(field_name="planned_amt", lookup_expr="gte")
    planned_max = df.NumberFilter(field_name="planned_amt", lookup_expr="lte")
    overlaps_date = df.DateFilter(method="filter_overlaps_date")

    class Meta:
        model = Milestone
        fields = ["project", "status", "due_from", "due_to", "planned_min", "planned_max", "overlaps_date"]

    def filter_overlaps_date(self, qs, name, value):
        # Return milestones whose slice range contains the given date
        return qs.filter(slice_start__lte=value, slice_end__gte=value)
