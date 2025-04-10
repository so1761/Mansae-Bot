from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import CustomUser

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'discord_username', 'global_name', 'avatar', 'avatar_url')  # 필요한 필드들
    search_fields = ('username', 'discord_username', 'global_name')  # 검색 필드
    list_filter = ('discord_username', 'global_name')  # 필터링 옵션
