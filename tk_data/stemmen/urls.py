from django.urls import path

from sync_db import views

urlpatterns = [
    path('', views.index),
]
