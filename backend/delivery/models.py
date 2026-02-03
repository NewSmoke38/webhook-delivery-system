from django.db import models
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
import uuid
import re


class FlexibleURLValidator(URLValidator):
    """
    Custom URL validator that accepts:
    - Standard URLs (http://example.com)
    - Docker service names (http://web:8000)
    - Localhost variations (http://localhost:8000)
    """
    
    def __call__(self, value):
        # Allow Docker service names (single word hostnames)
        # Pattern: http://servicename:port or http://servicename
        docker_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:'
            r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?'  # hostname (Docker service name)
            r'(?:\:[0-9]{1,5})?'  # optional port
            r')'
            r'(?:/.*)?$'  # optional path
        )
        
        if docker_pattern.match(value):
            return
        
        # Fall back to standard URL validation
        try:
            super().__call__(value)
        except ValidationError:
            raise ValidationError(
                'Enter a valid URL (e.g., http://example.com or http://web:8000)',
                code='invalid'
            )


class Destination(models.Model):
    """Represents a client/endpoint that wants to receive webhooks."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.CharField(
        max_length=500,
        validators=[FlexibleURLValidator()],
        help_text="The endpoint where we send the webhook"
    )
    secret_key = models.CharField(max_length=255, default=uuid.uuid4, help_text="Used for HMAC signature verification")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Destination {self.url}"


class Event(models.Model):
    """Represents a single webhook event received from an external source."""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name='events')
    payload = models.JSONField(help_text="The raw JSON body received from the webhook source")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    attempts_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Event {self.id} - {self.status}"


class DeliveryAttempt(models.Model):
    """Logs every single attempt to deliver an event to its destination."""
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20)
    response_status_code = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Attempt for Event {self.event_id} at {self.timestamp}"

