from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('get-started/', views.onboarding_start, name='onboarding_start'),
    path('get-started/details/', views.onboarding_details, name='onboarding_details'),
]
