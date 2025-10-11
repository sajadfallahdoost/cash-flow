from django.db import transaction
from django.utils.crypto import get_random_string
from django.core.cache import cache
from rest_framework import mixins, viewsets, status
from rest_framework.response import Response

IDEMPOTENCY_CACHE_PREFIX = "idem:"

class AtomicModelViewSet(viewsets.ModelViewSet):
    """
    Wraps write ops in DB transactions.
    """
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class IdempotencyMixin:
    """
    Simple idempotency for POST/PUT/PATCH via header:
      Idempotency-Key: <client-generated-unique-string>

    Stores response for a short window to prevent double-charges/double-creates.
    """
    idempotency_ttl = 60 * 10  # 10 minutes

    def _cache_key(self, key: str) -> str:
        return f"{IDEMPOTENCY_CACHE_PREFIX}{self.request.user.id}:{key}"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        self._idem_key = request.headers.get("Idempotency-Key")

    def finalize_response(self, request, response, *args, **kwargs):
        # Save successful write responses to cache
        if request.method in ("POST", "PUT", "PATCH") and self._idem_key:
            if 200 <= response.status_code < 300:
                cache.set(self._cache_key(self._idem_key), response.data, self.idempotency_ttl)
        return super().finalize_response(request, response, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Return cached response if key was seen
        key = request.headers.get("Idempotency-Key")
        if request.method in ("POST", "PUT", "PATCH") and key:
            cached = cache.get(self._cache_key(key))
            if cached is not None:
                return Response(cached, status=status.HTTP_200_OK)
        return super().dispatch(request, *args, **kwargs)
