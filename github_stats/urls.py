from django.urls import path

from . import views

app_name = 'github_stats'

urlpatterns = [
    path('summary/', views.summary, name='summary'),
    path('contributions/', views.contributions, name='contributions'),
    path('activity/', views.activity, name='activity'),
    path('projects/', views.projects, name='projects'),
]
