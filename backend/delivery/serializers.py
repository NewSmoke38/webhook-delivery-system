from rest_framework import serializers
from .models import Destination, Event


class DestinationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Destination
        fields = ['id', 'url', 'secret_key', 'is_active', 'created_at']
        read_only_fields = ['id', 'secret_key', 'created_at']
# Django auto-adds these fields! 

class EventSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Event
        fields = ['id', 'destination', 'payload', 'created_at']
        read_only_fields = ['id', 'created_at']

# Hidden from API: status, attempts (for internal use only)