from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Destination, Event
from .serializers import DestinationSerializer, EventSerializer
from .tasks import process_webhook_event  

# These endpoints let you manage webhook destinations (where webhooks go)
# Automatically creates these routes:
# - GET    /api/destinations/       → List all destinations
# - POST   /api/destinations/       → Create new destination
# - GET    /api/destinations/:id/   → Get specific destination
# - PUT    /api/destinations/:id/   → Update destination
# - DELETE /api/destinations/:id/   → Delete destination
# ============================================================================

class DestinationViewSet(viewsets.ModelViewSet):
    queryset = Destination.objects.all()
    serializer_class = DestinationSerializer


class EventViewSet(viewsets.ModelViewSet):
    """
    API for receiving and managing webhook events.
    
    POST /api/events/
    This is where webhooks come in!
    
    THE ASYNC PATTERN 
    
    ASYNCHRONOUS (What we do):
    Client sends webhook
      ↓
    API saves to database (takes <50ms)
      ↓
    API queues background task
      ↓
    API responds "202 Accepted" immediately ← CLIENT IS DONE!
      ↓
    [Meanwhile, in the background...]
      ↓
    Celery worker delivers webhook (can take as long as needed)
    """
    
    queryset = Event.objects.all()
    serializer_class = EventSerializer

    def create(self, request, *args, **kwargs):
        
        # Validate the incoming data
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  
        
        # Save to database (creates a new Event with status='PENDING')
        self.perform_create(serializer)

        event_instance = serializer.instance
        
        # .delay() sends this task to Redis and returns IMMEDIATELY
        process_webhook_event.delay(event_instance.id)
        
        # NOTE: We only pass the event ID, not the whole object
        # Why? Because Celery can't serialize Django model instances
        # The worker will fetch the full event from the database later
        
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            {
                "message": "Request accepted. Processing in background.", 
                "task_id": event_instance.id
            }, 
            status=status.HTTP_202_ACCEPTED,
            headers=headers
        )
        
