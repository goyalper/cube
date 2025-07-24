from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('multi_capture/', views.multi_capture, name='multi_capture'),
    path('multi_capture/capture/', views.multi_capture_face, name='multi_capture_face'),
    path('multi_reset/', views.multi_reset, name='multi_reset'),
    path('about/', views.about, name='about'),
    path('help/', views.help, name='help'),
]
