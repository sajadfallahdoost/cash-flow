from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
)
from .models import Milestone
from .serializers import MilestoneSerializer

ORDERABLE_FIELDS = {"id", "due_date", "planned_amt", "created_at", "updated_at"}

def _paginate(request, queryset):
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("page_size", 25))
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)
    return page_obj, {
        "count": paginator.count,
        "page": page_obj.number,
        "page_size": page_size,
        "num_pages": paginator.num_pages,
    }

def _apply_filters(request, qs):
    p = request.query_params

    # project / status
    project = p.get("project")
    if project:
        qs = qs.filter(project_id=project)

    status_ = p.get("status")
    if status_:
        qs = qs.filter(status__iexact=status_)

    # due_date range
    due_from = p.get("due_from")
    if due_from:
        qs = qs.filter(due_date__gte=due_from)
    due_to = p.get("due_to")
    if due_to:
        qs = qs.filter(due_date__lte=due_to)

    # planned amount range
    planned_min = p.get("planned_min")
    if planned_min:
        qs = qs.filter(planned_amt__gte=planned_min)
    planned_max = p.get("planned_max")
    if planned_max:
        qs = qs.filter(planned_amt__lte=planned_max)

    # overlaps a date inside slice
    overlaps_date = p.get("overlaps_date")
    if overlaps_date:
        qs = qs.filter(slice_start__lte=overlaps_date, slice_end__gte=overlaps_date)

    # search
    search = p.get("search")
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(project__name__icontains=search)
        )

    # ordering
    ordering = p.get("ordering", "due_date")
    if ordering.lstrip("-") in ORDERABLE_FIELDS:
        qs = qs.order_by(ordering)
    return qs

@extend_schema(
    parameters=[
        OpenApiParameter(name="project", description="Filter by project id", required=False, type=int),
        OpenApiParameter(name="status", description="Milestone status (planned/in_progress/done...)", required=False, type=str),
        OpenApiParameter(name="due_from", description="Due date ≥ (YYYY-MM-DD)", required=False, type=str),
        OpenApiParameter(name="due_to", description="Due date ≤ (YYYY-MM-DD)", required=False, type=str),
        OpenApiParameter(name="planned_min", description="planned_amt ≥", required=False, type=str),
        OpenApiParameter(name="planned_max", description="planned_amt ≤", required=False, type=str),
        OpenApiParameter(name="overlaps_date", description="Return items where slice_start..slice_end contains this date", required=False, type=str),
        OpenApiParameter(name="search", description="Search in name/description/project name", required=False, type=str),
        OpenApiParameter(name="ordering", description="One of id,due_date,planned_amt,created_at,updated_at (prefix '-' for desc)", required=False, type=str),
        OpenApiParameter(name="page", required=False, type=int),
        OpenApiParameter(name="page_size", required=False, type=int),
    ],
    request=MilestoneSerializer,
    responses={
        200: OpenApiResponse(response=MilestoneSerializer, description="List or created item"),
        201: MilestoneSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
    examples=[
        OpenApiExample(
            "Create Milestone",
            value={
                "project": 1,
                "name": "دهه دوم اسفند ۱۴۰۳",
                "description": "Invoice CF-2025-02 Slice B",
                "due_date": "2025-03-10",
                "planned_amt": "2500000.00",
                "status": "planned",
                "slice_start": "2025-03-11",
                "slice_end": "2025-03-20",
            },
            request_only=True,
        ),
    ],
)
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def milestones_list_create(request):
    if request.method == "GET":
        qs = _apply_filters(request, Milestone.objects.select_related("project").all())
        page_obj, meta = _paginate(request, qs)
        ser = MilestoneSerializer(page_obj.object_list, many=True)
        return Response({"results": ser.data, "meta": meta})

    # POST (atomic)
    with transaction.atomic():
        ser = MilestoneSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(MilestoneSerializer(obj).data, status=status.HTTP_201_CREATED)

@extend_schema(
    responses={
        200: MilestoneSerializer,
        204: OpenApiResponse(description="Deleted"),
        404: OpenApiResponse(description="Not found"),
        400: OpenApiResponse(description="Validation error"),
    },
    examples=[
        OpenApiExample(
            "Update Milestone (PATCH)",
            value={"status": "in_progress", "planned_amt": "3000000.00"},
            request_only=True,
        )
    ]
)
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def milestones_rud(request, pk: int):
    try:
        obj = Milestone.objects.select_related("project").get(pk=pk)
    except Milestone.DoesNotExist:
        return Response({"detail": "Not found."}, status=404)

    if request.method == "GET":
        return Response(MilestoneSerializer(obj).data)

    if request.method in ("PUT", "PATCH"):
        partial = request.method == "PATCH"
        with transaction.atomic():
            ser = MilestoneSerializer(instance=obj, data=request.data, partial=partial)
            ser.is_valid(raise_exception=True)
            obj = ser.save()
            return Response(MilestoneSerializer(obj).data)

    # DELETE
    with transaction.atomic():
        obj.delete()
        return Response(status=204)
