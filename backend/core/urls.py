from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from delivery.views import DestinationViewSet, EventViewSet


router = DefaultRouter()


router.register(r'destinations', DestinationViewSet)
router.register(r'events', EventViewSet)


urlpatterns = [
 
    # http://localhost:8000/admin/ 
    path('admin/', admin.site.urls),
    
    # All our REST API routes are under /api/
    # The router.urls includes all the routes we registered above 
    path('api/', include(router.urls)),
]

