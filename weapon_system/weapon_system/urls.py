"""
URL configuration for weapon_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('login/', views.discord_login, name='discord_login'),  # 디스코드 로그인 페이지로 이동
    path('logout/', views.discord_logout, name='discord_logout'),  # 디스코드 로그아웃 페이지로 이동
    path("api/discord/callback/", views.discord_callback),  # 디스코드 인증 후 리디렉션
    path("api/user/", views.user_info),
    path('api/weapon/<str:discord_username>/', views.get_weapon_data, name='get_weapon_data'),
    path("api/enhancement-info/", views.enhancement_info),
]
