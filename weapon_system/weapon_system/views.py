import requests
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth import login, logout
from accounts.models import CustomUser
from accounts.models import Weapon, Enhancement, Inheritance, Skill
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .firebase_config import initialize_firebase
from firebase_admin import db
import json
import os
from dotenv import load_dotenv

load_dotenv()
initialize_firebase()
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# 디스코드 로그인 페이지로 리다이렉트
def discord_login(request):
    # 디스코드 OAuth URL 생성
    oauth_url = f'https://discord.com/oauth2/authorize?client_id=1359041889936080896&response_type=code&redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Foauth%2Fredirect&scope=identify+email'
    return redirect(oauth_url)

@csrf_exempt
@require_http_methods(["POST"])  # GET ❌, POST ✅
def discord_callback(request):
    body = json.loads(request.body)
    code = body.get("code")

    if not code:
        return JsonResponse({"error": "No code provided"}, status=400)

    # 1. access_token 요청
    token_url = "https://discord.com/api/oauth2/token"
    payload = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_response = requests.post(token_url, data=payload, headers=headers)
    token_data = token_response.json()

    if "access_token" not in token_data:
        return JsonResponse({"error": "Failed to get access token", "details": token_data}, status=400)

    access_token = token_data["access_token"]

    # 2. Discord 유저 정보 가져오기
    user_info_url = "https://discord.com/api/users/@me"
    headers = {"Authorization": f"Bearer {access_token}"}
    user_response = requests.get(user_info_url, headers=headers)
    user_data = user_response.json()

    discord_id = user_data["id"]
    username = user_data["username"]
    global_name = user_data.get("global_name") or user_data["username"]
    avatar = user_data["avatar"]  # 이거도 중요!
    # 아바타 URL 생성
    avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar}.png" if avatar else None

    # 3. Django 유저 생성 or 조회
    # 3. Django 유저 조회
    try:
        user = CustomUser.objects.get(username=f"discord_{discord_id}")
    except CustomUser.DoesNotExist:
        user = CustomUser(username=f"discord_{discord_id}")
        user.set_unusable_password()
    
    user.id = discord_id
    user.discord_username = username  # 👈 이걸로 유저 표시 이름 저장
    user.global_name = global_name
    user.avatar = avatar
    user.avatar_url = avatar_url  # 아바타 URL을 저장
    user.save()

    # 4. Django 세션 로그인
    login(request, user)

    return JsonResponse({
        "message": "로그인 성공",
        "discord_user": user_data
    })


def discord_logout(request):
    logout(request)  # Django의 logout 함수로 세션 종료
    response = JsonResponse({"message": "Logged out"})
    response.delete_cookie("sessionid")  # 쿠키 삭제
    return response

# Firebase에서 데이터 가져오기
def get_weapon_data(request, discord_username):
    # Firebase 경로에서 무기 데이터 가져오기
    ref = db.reference(f"무기/유저/{discord_username}")
    weapon_data = ref.get()

    if not weapon_data:
        return JsonResponse({"error": "Weapon data not found"}, status=404)

    user_instance = CustomUser.objects.get(discord_username=discord_username)


    ref_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_base.get()

    ref_enhancement = db.reference(f"무기/강화")
    enhancement_options = ref_enhancement.get()
    
    weapon_type = weapon_data.get('무기타입')
    weapon_base_data = base_weapon_stats.get(weapon_type)  # 선택한 무기의 데이터

    ref_inherit_log = db.reference(f"무기/{discord_username}/계승 내역")
    inherit_log_data = ref_inherit_log.get() or {}
    
    # 계승 내역 적용 (기본 스탯 증가)
    inherit_level = inherit_log_data.get("기본 스탯 증가", 0)  # 계승 레벨 가져오기
    inherit_multiplier = inherit_level * 0.2  # 1마다 0.2배 증가

    base_attack_power = weapon_base_data.get("공격력", 0)
    base_durability = weapon_base_data.get("내구도", 0)
    base_accuracy = weapon_base_data.get("명중", 0)
    base_defense = weapon_base_data.get("방어력", 0)
    base_range = weapon_base_data.get("사거리", 0)
    base_speed = weapon_base_data.get("스피드", 0)
    base_skill_enhance = weapon_base_data.get("스킬 증폭", 0)
    base_critical_damage = weapon_base_data.get("치명타 대미지", 0)
    base_critical_hit_chance = weapon_base_data.get("치명타 확률", 0)
    

    ref_enhance_log = db.reference(f"무기/{discord_username}/강화내역")
    enhance_log_data = ref_enhance_log.get() or {}
    
    enhanced = {}
    for enhance_type, enhance_count in enhance_log_data.items():
        if enhance_type in enhancement_options:
            for stat, value in enhancement_options[enhance_type]["stats"].items():
                enhanced[stat] = round(enhanced.get(stat, 0) + value * enhance_count, 3)
                enhanced[stat] = round(enhanced[stat],3)

    # 무기 데이터 변환
    weapon = Weapon.objects.create(
        # 초기 스탯
        base_attack_power = base_attack_power,
        base_durability = base_durability,
        base_accuracy = base_accuracy,
        base_defense = base_defense,
        base_range = base_range,
        base_speed = base_speed,
        base_skill_enhance = base_skill_enhance,
        base_critical_damage = base_critical_damage,
        base_critical_hit_chance = base_critical_hit_chance,

        # 기본 스탯 증가
        base_increase_attack_power = round(base_attack_power * inherit_multiplier),
        base_increase_durability = round(base_durability * inherit_multiplier),
        base_increase_accuracy = round(base_accuracy * inherit_multiplier),
        base_increase_defense = round(base_defense * inherit_multiplier),
        base_increase_speed = round(base_speed * inherit_multiplier),
        base_increase_skill_enhance = round(base_skill_enhance * inherit_multiplier),
        
        # 강화 수치
        enhanced_attack_power=enhanced.get("공격력", 0),
        enhanced_durability=enhanced.get("내구도", 0),
        enhanced_accuracy=enhanced.get("명중", 0),
        enhanced_defense=enhanced.get("방어력", 0),
        enhanced_speed=enhanced.get("스피드", 0),
        enhanced_skill_enhance=enhanced.get("스킬 증폭", 0),
        enhanced_critical_damage=enhanced.get("치명타 대미지", 0),
        enhanced_critical_hit_chance=enhanced.get("치명타 확률", 0),

        # 최종 수치
        name=weapon_data.get('이름'),
        weapon_type=weapon_data.get('무기타입'),
        
        user = user_instance
    )

    # 강화 내역 처리
    enhancement_data = weapon_data.get('강화내역', {})
    enhancement = Enhancement.objects.create(
        weapon=weapon,
        attack_enhance=enhancement_data.get('공격 강화', 0),
        durability_enhance=enhancement_data.get('내구도 강화', 0),
        accuracy_enhance=enhancement_data.get('명중 강화', 0),
        speed_enhance=enhancement_data.get('속도 강화', 0),
        defense_enhance=enhancement_data.get('방어 강화', 0),
        skill_enhance=enhancement_data.get('스킬 강화', 0),
        critical_damage_enhance=enhancement_data.get('치명타 대미지 강화', 0),
        critical_hit_chance_enhance=enhancement_data.get('치명타 확률 강화', 0),
        balance_enhance=enhancement_data.get('밸런스 강화', 0),
        enhancement_level=weapon_data.get('강화', 0),
    )

    # 계승 내역 처리
    inheritance_data = weapon_data.get('계승 내역', {})
    inheritance = Inheritance.objects.create(
        weapon=weapon,
        base_stat_increase=inheritance_data.get('기본 스탯 증가', 0),
        base_skill_level_increase=inheritance_data.get('기본 스킬 레벨 증가', 0),
        additional_enhance=inheritance_data.get('추가강화', {}),
        inheritance_level=weapon_data.get('계승', 0),
    )

    # 스킬 처리
    skill_data = weapon_data.get('스킬', {})
    for skill_name, skill_info in skill_data.items():
        Skill.objects.create(
            weapon=weapon,
            skill_name=skill_name,
            level=skill_info.get('레벨', 0),
            cooldown=skill_info.get('전체 쿨타임', 0),
            current_cooldown=skill_info.get('현재 쿨타임', 0),
        )

    # 변환된 무기 정보를 반환
    return JsonResponse({
        'weapon': {
            'name': weapon.name,
            'weapon_type': weapon.weapon_type,
            'attack_power': {
                'base': weapon.base_attack_power,
                'inheritance': weapon.get_inheritance_value("attack_power"),
                'enhancement': weapon.get_enhancement_value("attack_power"),
            },
            'durability': {
                'base': weapon.base_durability,
                'inheritance': weapon.get_inheritance_value("durability"),
                'enhancement': weapon.get_enhancement_value("durability"),
            },
            'accuracy': {
                'base': weapon.base_accuracy,
                'inheritance': weapon.get_inheritance_value("accuracy"),
                'enhancement': weapon.get_enhancement_value("accuracy"),
            },
            'defense': {
                'base': weapon.base_defense,
                'inheritance': weapon.get_inheritance_value("defense"),
                'enhancement': weapon.get_enhancement_value("defense"),
            },
            'range': {
                'base': weapon.base_range,
                'inheritance': weapon.get_inheritance_value("range"),
                'enhancement': weapon.get_enhancement_value("range"),
            },
            'speed': {
                'base': weapon.base_speed,
                'inheritance': weapon.get_inheritance_value("speed"),
                'enhancement': weapon.get_enhancement_value("speed"),
            },
            'skill_enhance': {
                'base': weapon.base_skill_enhance,
                'inheritance': weapon.get_inheritance_value("skill_enhance"),
                'enhancement': weapon.get_enhancement_value("skill_enhance"),
            },
            'critical_damage': {
                'base': weapon.base_critical_damage,
                'inheritance': weapon.get_inheritance_value("critical_damage"),
                'enhancement': weapon.get_enhancement_value("critical_damage"),
            },
            'critical_hit_chance': {
                'base': weapon.base_critical_hit_chance,
                'inheritance': weapon.get_inheritance_value("critical_hit_chance"),
                'enhancement': weapon.get_enhancement_value("critical_hit_chance"),
            },
        },
        'enhancements': {
            'attack_enhance': enhancement.attack_enhance,
            'durability_enhance': enhancement.durability_enhance,
            'accuracy_enhance': enhancement.accuracy_enhance,
            'speed_enhance': enhancement.speed_enhance,
            'enhancement_level': enhancement.enhancement_level,
        },
        'inheritance': {
            'base_stat_increase': inheritance.base_stat_increase,
            'base_skill_level_increase': inheritance.base_skill_level_increase,
            'additional_enhance': inheritance.additional_enhance,
            'inheritance_level': inheritance.inheritance_level,
        },
        'skills': [
            {
                'skill_name': skill.skill_name,
                'level': skill.level,
                'cooldown': skill.cooldown,
                'current_cooldown': skill.current_cooldown,
            } for skill in Skill.objects.filter(weapon=weapon)
        ]
    }, safe=False)

def enhancement_info(request):
    ref = db.reference('무기/강화')
    data = ref.get()
    return JsonResponse(data)

def user_info(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    return JsonResponse({
        "global_name": request.user.global_name,
        "discord_username": request.user.discord_username,
        "avatar_url": request.user.avatar_url
    })