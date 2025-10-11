import django_filters as df

class DateFromToFilter(df.FilterSet):
    created_from = df.DateFilter(field_name="created_at", lookup_expr="gte")
    created_to   = df.DateFilter(field_name="created_at", lookup_expr="lte")
    updated_from = df.DateFilter(field_name="updated_at", lookup_expr="gte")
    updated_to   = df.DateFilter(field_name="updated_at", lookup_expr="lte")


class DecimalRangeFilter(df.FilterSet):
    amount_min = df.NumberFilter(field_name="amount", lookup_expr="gte")
    amount_max = df.NumberFilter(field_name="amount", lookup_expr="lte")
