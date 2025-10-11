from rest_framework import serializers
from .models import Milestone

class MilestoneSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    is_overdue = serializers.SerializerMethodField()
    slice_range = serializers.SerializerMethodField()

    class Meta:
        model = Milestone
        fields = [
            "id", "project", "project_name",
            "name", "description",
            "due_date",
            "planned_amt",
            "status",
            "slice_start", "slice_end", "slice_range",
            "is_overdue",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "project_name", "is_overdue", "slice_range"]

    def get_is_overdue(self, obj):
        from django.utils.timezone import now
        return obj.due_date < now().date() and obj.status != "done"

    def get_slice_range(self, obj):
        if obj.slice_start and obj.slice_end:
            return f"{obj.slice_start}…{obj.slice_end}"
        return None
