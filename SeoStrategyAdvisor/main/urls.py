from django.contrib import admin
from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('signin/',views.signin, name='signin'),
    path('signout/',views.signout, name='signout'),
    path('signup/',views.signup, name='signup'),
    path('profile/',views.profile, name='profile'),
    path('analysis/<int:analysis_id>/', views.analysis_result, name='analysis_results'),
    path('contactus/', views.contact_us, name='contact_us'),
    path('contact_success/', views.contact_success, name= 'contact_success'),
    path('about/',views.about_us, name='about_us'),
    path('blog/post/',views.blog_post, name ='blog_post')
]