from django.db import transaction as dbtx
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
)
from .models import Category, Transaction
from .serializers import CategorySerializer, TransactionSerializer

ORDERABLE_TX_FIELDS = {"id", "txn_date", "amount", "created_at", "updated_at"}
ORDERABLE_CAT_FIELDS = {"id", "name", "sort_order", "created_at", "updated_at"}


# ------------------------------ helpers ------------------------------
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

def _apply_tx_filters(request, qs):
    p = request.query_params

    # company (required for most screens; optional here)
    company = p.get("company")
    if company:
        qs = qs.filter(company_id=company)

    # project / milestone
    project = p.get("project")
    if project:
        qs = qs.filter(project_id=project)

    milestone = p.get("milestone")
    if milestone:
        qs = qs.filter(milestone_id=milestone)

    # category (single, list, or negation: "!2" or "3,5,8")
    category = p.get("category")
    if category:
        raw = category.strip()
        exclude = raw.startswith("!")
        ids = [int(x) for x in raw.lstrip("!").split(",") if x.isdigit()]
        if ids:
            expr = {"category_id__in": ids}
            qs = qs.exclude(**expr) if exclude else qs.filter(**expr)

    # category type (income/expense/etc. per TransactionType)
    t_type = p.get("t_type")
    if t_type:
        qs = qs.filter(category__t_type__iexact=t_type)

    # currency
    currency = p.get("currency")
    if currency:
        qs = qs.filter(currency__iexact=currency)

    # import ref
    import_ref = p.get("import_ref")
    if import_ref:
        qs = qs.filter(import_ref_id=import_ref)

    # amount range
    amount_min = p.get("amount_min")
    if amount_min:
        qs = qs.filter(amount__gte=amount_min)
    amount_max = p.get("amount_max")
    if amount_max:
        qs = qs.filter(amount__lte=amount_max)

    # date range
    txn_from = p.get("txn_from")
    if txn_from:
        qs = qs.filter(txn_date__gte=txn_from)
    txn_to = p.get("txn_to")
    if txn_to:
        qs = qs.filter(txn_date__lte=txn_to)

    # created/updated windows
    created_from = p.get("created_from")
    if created_from:
        qs = qs.filter(created_at__gte=created_from)
    created_to = p.get("created_to")
    if created_to:
        qs = qs.filter(created_at__lte=created_to)
    updated_from = p.get("updated_from")
    if updated_from:
        qs = qs.filter(updated_at__gte=updated_from)
    updated_to = p.get("updated_to")
    if updated_to:
        qs = qs.filter(updated_at__lte=updated_to)

    # simple search
    search = p.get("search")
    if search:
        qs = qs.filter(
            Q(description__icontains=search) |
            Q(category__name__icontains=search) |
            Q(project__name__icontains=search) |
            Q(milestone__name__icontains=search)
        )

    # ordering
    ordering = p.get("ordering", "-txn_date")
    if ordering.lstrip("-") in ORDERABLE_TX_FIELDS:
        qs = qs.order_by(ordering)

    return qs


# ------------------------------ Transactions ------------------------------
@extend_schema(
    tags=["Transactions"],
    parameters=[
        OpenApiParameter("company",     int,  OpenApiParameter.QUERY, description="Company ID"),
        OpenApiParameter("project",     int,  OpenApiParameter.QUERY, description="Project ID"),
        OpenApiParameter("milestone",   int,  OpenApiParameter.QUERY, description="Milestone ID"),
        OpenApiParameter("category",    str,  OpenApiParameter.QUERY, description="Category ID(s): '3' | '3,5,8' | '!2'"),
        OpenApiParameter("t_type",      str,  OpenApiParameter.QUERY, description="Category TransactionType (e.g., 'income'/'expense')"),
        OpenApiParameter("currency",    str,  OpenApiParameter.QUERY, description="ISO code (e.g., IRR, USD)"),
        OpenApiParameter("import_ref",  int,  OpenApiParameter.QUERY, description="SpreadsheetImport ID"),
        OpenApiParameter("amount_min",  str,  OpenApiParameter.QUERY, description="amount ≥"),
        OpenApiParameter("amount_max",  str,  OpenApiParameter.QUERY, description="amount ≤"),
        OpenApiParameter("txn_from",    str,  OpenApiParameter.QUERY, description="txn_date ≥ (YYYY-MM-DD)"),
        OpenApiParameter("txn_to",      str,  OpenApiParameter.QUERY, description="txn_date ≤ (YYYY-MM-DD)"),
        OpenApiParameter("created_from",str,  OpenApiParameter.QUERY),
        OpenApiParameter("created_to",  str,  OpenApiParameter.QUERY),
        OpenApiParameter("updated_from",str,  OpenApiParameter.QUERY),
        OpenApiParameter("updated_to",  str,  OpenApiParameter.QUERY),
        OpenApiParameter("search",      str,  OpenApiParameter.QUERY, description="description/category/project/milestone"),
        OpenApiParameter("ordering",    str,  OpenApiParameter.QUERY, description="id,txn_date,amount,created_at,updated_at (prefix '-' for desc)"),
        OpenApiParameter("page",        int,  OpenApiParameter.QUERY),
        OpenApiParameter("page_size",   int,  OpenApiParameter.QUERY),
    ],
    request=TransactionSerializer,
    responses={
        200: OpenApiResponse(description="List", response=TransactionSerializer),
        201: TransactionSerializer,
        400: OpenApiResponse(description="Validation error"),
    },
    examples=[
        OpenApiExample(
            "Create Transaction",
            value={
                "company": 1,
                "project": 2,
                "category": 5,
                "milestone": 12,
                "txn_date": "2025-03-12",
                "amount": "1750000.00",
                "currency": "IRR",
                "description": "Advance payment for CF-02",
            },
            request_only=True,
        )
    ],
)
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def transactions_list_create(request):
    if request.method == "GET":
        qs = _apply_tx_filters(
            request,
            Transaction.objects.select_related(
                "company", "project", "category", "milestone"
            ).all()
        )
        ser = TransactionSerializer(qs, many=True)
        return Response(ser.data)

    # POST (atomic)
    with dbtx.atomic():
        ser = TransactionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(TransactionSerializer(obj).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=["Transactions"],
    responses={
        200: TransactionSerializer,
        204: OpenApiResponse(description="Deleted"),
        404: OpenApiResponse(description="Not found"),
        400: OpenApiResponse(description="Validation error"),
    },
    examples=[
        OpenApiExample("Patch amount", value={"amount": "2500000.00"}, request_only=True),
        OpenApiExample("Patch description", value={"description": "Adjusted after supplier discount"}, request_only=True),
    ],
)
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def transactions_rud(request, pk: int):
    try:
        obj = Transaction.objects.select_related("company", "project", "category", "milestone").get(pk=pk)
    except Transaction.DoesNotExist:
        return Response({"detail": "Not found."}, status=404)

    if request.method == "GET":
        return Response(TransactionSerializer(obj).data)

    if request.method in ("PUT", "PATCH"):
        partial = request.method == "PATCH"
        with dbtx.atomic():
            ser = TransactionSerializer(instance=obj, data=request.data, partial=partial)
            ser.is_valid(raise_exception=True)
            obj = ser.save()
            return Response(TransactionSerializer(obj).data)

    with dbtx.atomic():
        obj.delete()
        return Response(status=204)


@extend_schema(
    tags=["Transactions"],
    summary="Summary totals (respects current filters)",
    parameters=[
        OpenApiParameter("company",    int,  OpenApiParameter.QUERY),
        OpenApiParameter("project",    int,  OpenApiParameter.QUERY),
        OpenApiParameter("milestone",  int,  OpenApiParameter.QUERY),
        OpenApiParameter("category",   str,  OpenApiParameter.QUERY),
        OpenApiParameter("t_type",     str,  OpenApiParameter.QUERY),
        OpenApiParameter("currency",   str,  OpenApiParameter.QUERY),
        OpenApiParameter("amount_min", str,  OpenApiParameter.QUERY),
        OpenApiParameter("amount_max", str,  OpenApiParameter.QUERY),
        OpenApiParameter("txn_from",   str,  OpenApiParameter.QUERY),
        OpenApiParameter("txn_to",     str,  OpenApiParameter.QUERY),
    ],
    responses={
        200: OpenApiResponse(
            description="[{'currency': 'IRR', 'total': '4250000.00'}]",
        )
    },
    examples=[
        OpenApiExample(
            "Totals per currency",
            value=[{"currency": "IRR", "total": "4250000.00"}, {"currency": "USD", "total": "900.00"}],
            response_only=True,
        ),
        OpenApiExample(
            "Totals per category (alt example)",
            value=[{"category_id": 5, "category_name": "Equipment", "total": "3200000.00"}],
            response_only=True,
        ),
    ],
)
@api_view(["GET"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def transactions_summary(request):
    """
    Returns totals grouped by currency. Add `group_by=category` to group by category instead.
    """
    qs = _apply_tx_filters(
        request,
        Transaction.objects.select_related("category").all()
    )
    group_by = request.query_params.get("group_by")
    if group_by == "category":
        data = qs.values("category_id", "category__name") \
                 .annotate(total=Sum("amount")).order_by("category__name")
        out = [{"category_id": r["category_id"], "category_name": r["category__name"], "total": r["total"]} for r in data]
        return Response(out)
    else:
        data = qs.values("currency").annotate(total=Sum("amount")).order_by("currency")
        return Response(list(data))


# ------------------------------ Categories ------------------------------
@extend_schema(
    tags=["Categories"],
    parameters=[
        OpenApiParameter("active", bool, OpenApiParameter.QUERY, description="Filter active categories"),
        OpenApiParameter("t_type", str,  OpenApiParameter.QUERY, description="TransactionType of category"),
        OpenApiParameter("parent", int,  OpenApiParameter.QUERY, description="Filter by parent id"),
        OpenApiParameter("search", str,  OpenApiParameter.QUERY, description="Search in name"),
        OpenApiParameter("ordering", str, OpenApiParameter.QUERY, description="id,name,sort_order,created_at,updated_at"),
        OpenApiParameter("page", int, OpenApiParameter.QUERY),
        OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
    ],
    request=CategorySerializer,
    responses={200: OpenApiResponse(description="List", response=CategorySerializer), 201: CategorySerializer},
    examples=[OpenApiExample("Create Category", value={"name": "Equipment", "t_type": "expense", "sort_order": 10})],
)
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def categories_list_create(request):
    if request.method == "GET":
        p = request.query_params
        qs = Category.objects.all()

        if "active" in p:
            val = p.get("active", "").lower()
            if val in ("true", "1"):
                qs = qs.filter(is_active=True)
            elif val in ("false", "0"):
                qs = qs.filter(is_active=False)

        if p.get("t_type"):
            qs = qs.filter(t_type__iexact=p.get("t_type"))

        if p.get("parent"):
            qs = qs.filter(parent_id=p.get("parent"))

        if p.get("search"):
            qs = qs.filter(name__icontains=p.get("search"))

        ordering = p.get("ordering", "sort_order")
        if ordering.lstrip("-") in ORDERABLE_CAT_FIELDS:
            qs = qs.order_by(ordering, "id")

        ser = CategorySerializer(qs, many=True)
        return Response(ser.data)

    with dbtx.atomic():
        ser = CategorySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        return Response(CategorySerializer(obj).data, status=201)

@extend_schema(
    tags=["Categories"],
    responses={200: CategorySerializer, 204: OpenApiResponse(description="Deleted"), 404: OpenApiResponse(description="Not found")},
)
@api_view(["GET", "PUT", "PATCH", "DELETE"])
@permission_classes([permissions.IsAuthenticatedOrReadOnly])
def categories_rud(request, pk: int):
    try:
        obj = Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        return Response({"detail": "Not found."}, status=404)

    if request.method == "GET":
        return Response(CategorySerializer(obj).data)

    if request.method in ("PUT", "PATCH"):
        partial = request.method == "PATCH"
        with dbtx.atomic():
            ser = CategorySerializer(instance=obj, data=request.data, partial=partial)
            ser.is_valid(raise_exception=True)
            obj = ser.save()
            return Response(CategorySerializer(obj).data)

    with dbtx.atomic():
        obj.delete()
        return Response(status=204)
