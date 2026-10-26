from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/contact/', include('contact.urls')),
    path('api/github/', include('github_stats.urls')),
]
