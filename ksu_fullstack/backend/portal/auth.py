from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    """Token auth whose tokens stop working after TOKEN_TTL_HOURS."""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        ttl = timedelta(hours=getattr(settings, "TOKEN_TTL_HOURS", 12))
        if timezone.now() - token.created > ttl:
            token.delete()
            raise AuthenticationFailed("Session expired. Please sign in again.")
        return user, token
