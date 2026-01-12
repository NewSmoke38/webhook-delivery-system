import hashlib
import hmac
import requests
import logging
from celery import shared_task
from django.utils import timezone
from .models import Event, Destination, DeliveryAttempt

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,              
    max_retries=3,          
    default_retry_delay=60  
)
def process_webhook_event(self, event_id):

    try:
        # Fetch event and destination from database
        try:
            event = Event.objects.select_related('destination').get(id=event_id)
        except Event.DoesNotExist:
            logger.error(f"Event {event_id} not found in database")
            return {"status": "error", "message": "Event not found"}
        
        destination = event.destination
        
        if not destination.is_active:
            logger.warning(f"Destination {destination.id} is inactive, skipping delivery")
            event.status = 'FAILED'
            event.save()
            return {"status": "skipped", "message": "Destination is inactive"}
        
        event.status = 'PROCESSING'
        event.attempts_count += 1
        event.save()
        
        logger.info(f"Processing event {event_id} for destination {destination.url}")
        
        import json
        payload_string = json.dumps(event.payload, sort_keys=True)
        
        signature = hmac.new(
            key=str(destination.secret_key).encode('utf-8'),
            msg=payload_string.encode('utf-8'),
            digestmod=hashlib.sha256
        ).hexdigest()
        
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,  
            'X-Event-ID': str(event.id),        
            'User-Agent': 'WebhookDeliverySystem/1.0'
        }
        
        try:
            response = requests.post(
                url=destination.url,
                json=event.payload,
                headers=headers,
                timeout=30
            )
            
            response_status_code = response.status_code
            response_body = response.text[:1000]  
            
            logger.info(f"Webhook delivered to {destination.url}, status: {response_status_code}")
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout delivering to {destination.url}")
            response_status_code = 0
            response_body = "Request timeout after 30 seconds"
            
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error to {destination.url}")
            response_status_code = 0
            response_body = "Connection error - destination unreachable"
            
        except Exception as e:
            logger.error(f"Unexpected error delivering webhook: {str(e)}")
            response_status_code = 0
            response_body = f"Unexpected error: {str(e)}"
                
        is_successful = 200 <= response_status_code < 300
        is_client_error = 400 <= response_status_code < 500
        

        DeliveryAttempt.objects.create(
            event=event,
            status='SUCCESS' if is_successful else 'FAILED',
            response_status_code=response_status_code,
            response_body=response_body,
            timestamp=timezone.now()
        )
        
        if is_successful:
            event.status = 'SUCCESS'
            event.save()
            logger.info(f" Event {event_id} delivered successfully!")
            return {
                "status": "success",
                "event_id": str(event_id),
                "status_code": response_status_code
            }
        
        elif is_client_error:
            event.status = 'FAILED'
            event.save()
            logger.error(f" Client error {response_status_code}, not retrying")
            return {
                "status": "failed",
                "event_id": str(event_id),
                "reason": "client_error",
                "status_code": response_status_code
            }
        
        else:
            logger.warning(f" Server error {response_status_code}, will retry...")
            
            raise Exception(
                f"Server error or network issue (code: {response_status_code})"
            )
    
    except Exception as exc:
        
        if self.request.retries < self.max_retries:
            # Retry 1: 60 seconds
            # Retry 2: 120 seconds (2^1 * 60)
            # Retry 3: 240 seconds (2^2 * 60)
            retry_delay = 60 * (2 ** self.request.retries)
            
            logger.warning(
                f"Retry {self.request.retries + 1}/{self.max_retries} "
                f"for event {event_id} in {retry_delay} seconds"
            )
            
            raise self.retry(exc=exc, countdown=retry_delay)
        else:
            logger.error(f" Max retries reached for event {event_id}, marking as FAILED")
            
            try:
                event = Event.objects.get(id=event_id)
                event.status = 'FAILED'
                event.save()
            except Event.DoesNotExist:
                pass
            
            return {
                "status": "failed",
                "event_id": str(event_id),
                "reason": "max_retries_exceeded"
            }


# helper function to verify webhook signature when recieving them

def verify_webhook_signature(payload, signature, secret_key):
    import json
    
    if isinstance(payload, dict):
        payload = json.dumps(payload, sort_keys=True)
    
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    expected_signature = hmac.new(
        key=str(secret_key).encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)
