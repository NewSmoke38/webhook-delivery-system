from rest_framework import serializers
from .models import Destination, Event
import re


class FlexibleURLField(serializers.CharField):
    """Custom URL field that accepts Docker service names and standard URLs"""
    
    def to_internal_value(self, data):
        # First get the string value
        value = super().to_internal_value(data)
        
        # Check if it's a valid URL pattern (including Docker service names)
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:'
            r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*)|'  # domain name
            r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?|'  # single hostname (Docker service)
            r'localhost'  # localhost
            r')'
            r'(?:\:[0-9]{1,5})?'  # optional port
            r'(?:/.*)?$',  # optional path
            re.IGNORECASE
        )
        
        if not url_pattern.match(value):
            raise serializers.ValidationError('Enter a valid URL.')
        
        return value


class DestinationSerializer(serializers.ModelSerializer):
    url = FlexibleURLField()
    
    class Meta:
        model = Destination
        fields = ['id', 'url', 'secret_key', 'is_active', 'created_at']
        read_only_fields = ['id', 'secret_key', 'created_at']


class EventSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Event
        fields = ['id', 'destination', 'payload', 'created_at']
        read_only_fields = ['id', 'created_at']

