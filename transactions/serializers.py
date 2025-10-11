from rest_framework import serializers
from .models import Category, Transaction
from milestones.models import Milestone
from core.models import Project

class CategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", read_only=True)

    class Meta:
        model = Category
        fields = [
            "id", "parent", "parent_name",
            "name", "t_type", "sort_order", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at", "parent_name"]


class TransactionSerializer(serializers.ModelSerializer):
    company_name   = serializers.CharField(source="company.name", read_only=True)
    project_name   = serializers.CharField(source="project.name", read_only=True)
    category_name  = serializers.CharField(source="category.name", read_only=True)
    milestone_name = serializers.CharField(source="milestone.name", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "company", "company_name",
            "project", "project_name",
            "category", "category_name",
            "milestone", "milestone_name",
            "import_ref",
            "txn_date", "amount", "currency", "description",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "created_at", "updated_at",
            "company_name", "project_name", "category_name", "milestone_name",
        ]

    # --- Optional data integrity checks across FKs (safe if your Project/Milestone carry company) ---
    def validate(self, data):
        company  = data.get("company")  or getattr(self.instance, "company",  None)
        project  = data.get("project")  or getattr(self.instance, "project",  None)
        milestone= data.get("milestone")or getattr(self.instance, "milestone",None)

        # If Project has a 'company' FK, enforce consistency
        if company and project and hasattr(project, "company") and project.company_id != company.id:
            raise serializers.ValidationError({"project": "Project does not belong to the given company."})

        # If Milestone -> Project -> Company chain exists, enforce consistency
        if company and milestone:
            proj = getattr(milestone, "project", None)
            if proj and hasattr(proj, "company") and proj.company_id != company.id:
                raise serializers.ValidationError({"milestone": "Milestone’s project company mismatches transaction company."})

        return data
