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
import random
import json
import os
import discord
from dotenv import load_dotenv


def mission_notice(name, mission):
    load_dotenv()
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    title = "시즌 미션 달성!"
    description = f"{name}님이 [{mission}] 미션을 달성했습니다!"

    embed = {
        "title": title,
        "description": description,
        "color": discord.Color.light_gray().value
    }

    webhook_data = {
        "username": "미션 알림",
        "embeds": [embed]
    }

    resp = requests.post(WEBHOOK_URL, json=webhook_data)
    if resp.status_code != 204:
        print(f"웹후크 전송 실패: {resp.status_code}")

load_dotenv()
initialize_firebase()
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
DISCORD_ENHANCE_WEBHOOK_URL = os.getenv("DISCORD_ENHANCE_WEBHOOK_URL")
DISCORD_OAUTH_URL = os.getenv("DISCORD_OAUTH_URL")
# 디스코드 로그인 페이지로 리다이렉트
def discord_login(request):
    # 디스코드 OAuth URL 생성
    oauth_url = DISCORD_OAUTH_URL
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

    user_instance = CustomUser.objects.filter(discord_username=discord_username).first()


    ref_base = db.reference(f"무기/기본 스탯")
    base_weapon_stats = ref_base.get()

    ref_enhancement = db.reference(f"무기/강화")
    enhancement_options = ref_enhancement.get()
    
    weapon_type = weapon_data.get('무기타입')
    weapon_base_data = base_weapon_stats.get(weapon_type)  # 선택한 무기의 데이터

    ref_inherit_log = db.reference(f"무기/유저/{discord_username}/계승 내역")
    inherit_log_data = ref_inherit_log.get() or {}
    
    # 계승 내역 적용 (기본 스탯 증가)
    inherit_level = inherit_log_data.get("기본 스탯 증가", 0)  # 계승 레벨 가져오기
    inherit_multiplier = inherit_level * 0.3  # 1마다 0.3배 증가
    base_attack_power = weapon_base_data.get("공격력", 0)
    base_durability = weapon_base_data.get("내구도", 0)
    base_accuracy = weapon_base_data.get("명중", 0)
    base_defense = weapon_base_data.get("방어력", 0)
    base_speed = weapon_base_data.get("스피드", 0)
    base_skill_enhance = weapon_base_data.get("스킬 증폭", 0)
    base_critical_damage = weapon_base_data.get("치명타 대미지", 0)
    base_critical_hit_chance = weapon_base_data.get("치명타 확률", 0)
    

    ref_enhance_log = db.reference(f"무기/유저/{discord_username}/강화내역")
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
        accuracy_enhance=enhancement_data.get('명중 강화', 0),
        speed_enhance=enhancement_data.get('속도 강화', 0),
        defense_enhance=enhancement_data.get('방어 강화', 0),
        skill_enhance=enhancement_data.get('스킬 강화', 0),
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
    ref_weapon_stats = db.reference(f"무기/유저/{discord_username}")
    weapon_stats_data = ref_weapon_stats.get() or {}

    for skill_name, skill_info in skill_data.items():
        ref_skill_data = db.reference(f"무기/스킬/{skill_name}")
        skill_server_data = ref_skill_data.get() or {}

        # 공통 values
        values = skill_server_data.get('values', {})
        level = skill_info.get('레벨', 1)  # 없으면 1로 가정

        # 공통 cooldown
        cooldown_data = skill_server_data.get("cooldown", {})
        total_cd = cooldown_data.get("전체 쿨타임", 0)
        current_cd = cooldown_data.get("현재 쿨타임", 0)

        # 템플릿 변수로 사용할 딕셔너리
        template_context = {
            **values,
            '레벨': level,
            '공격력': weapon_stats_data.get('공격력', 0),
            '스킬_증폭': weapon_stats_data.get('스킬 증폭', 0),
            '명중': weapon_stats_data.get('명중', 0),
            '스피드': weapon_stats_data.get('스피드', 0),
            '내구도': weapon_stats_data.get('내구도', 0),
            '방어력': weapon_stats_data.get('방어력', 0),
            '치명타_확률': weapon_stats_data.get('치명타 확률', 0),
            '치명타_대미지': weapon_stats_data.get('치명타 대미지', 0),
        }

        tooltip_key = skill_server_data.get('tooltip', None)

        Skill.objects.create(
            weapon=weapon,
            skill_name=skill_name,
            level=level,
            cooldown=total_cd,
            current_cooldown=current_cd,
            skill_description=skill_server_data.get('description', "스킬 설명이 없습니다"),
            skill_notes_key=tooltip_key,
            skill_notes_params=template_context  # 💡 JSONField여야 함
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
            'defense_enhance': enhancement.defense_enhance,
            'accuracy_enhance': enhancement.accuracy_enhance,
            'speed_enhance': enhancement.speed_enhance,
            'balance_enhance': enhancement.balance_enhance,
            'skill_enhance': enhancement.skill_enhance,
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
                'skill_description': skill.skill_description,
                'skill_notes_key': skill.skill_notes_key,
                'skill_notes_params': skill.skill_notes_params
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

def get_items(request, discord_username):

    item_ref = db.reference(f'무기/아이템/{discord_username}')
    data = item_ref.get()
    return JsonResponse(data)

@csrf_exempt
def enhance_weapon(request):
    if request.method == 'POST':
        try:
            # JSON 본문 파싱
            body = json.loads(request.body)

            # 각각의 값 가져오기
            discord_username = body.get('discord_username')
            enhance_type = body.get('enhanceType')
            use_polish = body.get('usePolish')
            use_high_polish = body.get('useHighPolish')

            enhance_type = enhance_type[0]

            enhancement_probabilities = {
                0: 100,  # 0강 - 100% 성공
                1: 90,   # 1강 - 90% 성공
                2: 90,   # 2강 - 90% 성공
                3: 80,   # 3강 - 80% 성공
                4: 80,   # 4강 - 80% 성공
                5: 80,   # 5강 - 80% 성공
                6: 70,   # 6강 - 70% 성공
                7: 60,   # 7강 - 60% 성공
                8: 60,   # 8강 - 60% 성공
                9: 40,   # 9강 - 40% 성공
                10: 40,  # 10강 - 40% 성공
                11: 30,  # 11강 - 30% 성공
                12: 20,  # 12강 - 20% 성공
                13: 20,  # 13강 - 20% 성공
                14: 10,  # 14강 - 10% 성공
                15: 10,  # 15강 - 10% 성공
                16: 5,  # 16강 - 5% 성공
                17: 5,  # 17강 - 5% 성공
                18: 3,  # 18강 - 3% 성공
                19: 1,   # 19강 - 1% 성공
            }
            nickname = discord_username

            ref_weapon = db.reference(f"무기/유저/{nickname}")
            weapon_data = ref_weapon.get() or {}
            ref_item = db.reference(f"무기/아이템/{nickname}")
            item_data = ref_item.get() or {}
            weapon_enhanced = weapon_data.get("강화", 0)
            weapon_parts = item_data.get("강화재료", 0)

            # 재료 부족 예외 처리
            if weapon_parts <= 0:
                return JsonResponse({'error': '강화 재료가 부족합니다.'}, status=400)

            if use_polish:
                polish_count = item_data.get("연마제", 0)
                if polish_count <= 0:
                    return JsonResponse({'error': '연마제가 부족합니다.'}, status=400)

            if use_high_polish:
                special_polish_count = item_data.get("특수 연마제", 0)
                if special_polish_count <= 0:
                    return JsonResponse({'error': '특수 연마제가 부족합니다.'}, status=400)
                
            ref_item.update({"강화재료": weapon_parts - 1})

            enhancement_rate = enhancement_probabilities[weapon_enhanced]
            if use_polish:
                enhancement_rate += 5
                # 연마제 차감
                item_ref = db.reference(f"무기/아이템/{nickname}")
                current_items = item_ref.get() or {}
                polish_count = current_items.get("연마제", 0)
                if polish_count > 0:
                    item_ref.update({"연마제": polish_count - 1})
            if use_high_polish:
                enhancement_rate += 50
                # 특수 연마제 차감
                item_ref = db.reference(f"무기/아이템/{nickname}")
                current_items = item_ref.get() or {}
                special_polish_count = current_items.get("특수 연마제", 0)
                if special_polish_count > 0:
                    item_ref.update({"특수 연마제": special_polish_count - 1})

            roll = random.randint(1, 100)
            success = roll <= enhancement_rate
            if success:  # 성공
                ref_weapon.update({"강화" : weapon_enhanced + 1})
                ref_weapon_log = db.reference(f"무기/유저/{nickname}/강화내역")
                weapon_log_data = ref_weapon_log.get() or {}

                original_enhancement = weapon_log_data.get(enhance_type,0)
                ref_weapon_log.update({enhance_type : original_enhancement + 1}) # 선택한 강화 + 1
                # 무기의 기존 스탯 가져오기
                weapon_stats = {key: value for key, value in weapon_data.items() if key not in ["강화","이름","강화내역"]}

                # 강화 옵션 가져오기
                ref_weapon_enhance = db.reference(f"무기/강화")
                enhancement_options = ref_weapon_enhance.get() or {}
                options = enhancement_options.get(enhance_type, enhancement_options["밸런스 강화"])
                stats = options["stats"]  # 실제 강화 수치가 있는 부분

                # 스탯 적용
                for stat, base_increase in stats.items():
                    # 선택한 스탯은 특화 배율 적용
                    increase = base_increase  # 기본 배율 적용
                    final_stat = weapon_stats.get(stat, 0) + increase
                    
                    weapon_stats[stat] = final_stat

                # ====================  [미션]  ====================
                # 시즌미션 : 연마(무기 20강 달성)
                if weapon_enhanced + 1 == 20:
                    ref_mission = db.reference(f"미션/미션진행상태/{nickname}/시즌미션/연마")
                    mission_data = ref_mission.get() or {}
                    mission_bool = mission_data.get('완료',False)
                    if not mission_bool:
                        ref_mission.update({"완료": True})
                        mission_notice(nickname,"연마")
                        print(f"{nickname}의 [연마] 미션 완료")
                # ====================  [미션]  ====================
                        
                # ====================  [미션]  ====================
                # 시즌미션 : 6종의 인장 미션
                if weapon_enhanced + 1 == 20:
                    ref_enhance = db.reference(f"무기/유저/{nickname}/강화내역")
                    ref_inherit = db.reference(f"무기/유저/{nickname}/계승 내역/추가강화")
                    
                    enhance_data = ref_enhance.get() or {}
                    inherit_data = ref_inherit.get() or {}

                    # 시즌미션 이름 매핑: {강화이름: 미션명}
                    mission_targets = {
                        "공격 강화": "맹공",
                        "스킬 강화": "현자",
                        "명중 강화": "집중",
                        "속도 강화": "신속",
                        "방어 강화": "경화",
                        "밸런스 강화": "균형"
                    }

                    for stat_name, mission_name in mission_targets.items():
                        total = enhance_data.get(stat_name, 0)
                        inherited = inherit_data.get(stat_name, 0)
                        actual = total - inherited

                        if actual == 20:
                            ref_mission = db.reference(f"미션/미션진행상태/{nickname}/시즌미션/{mission_name}")
                            mission_data = ref_mission.get() or {}
                            if not mission_data.get("완료", False):
                                ref_mission.update({"완료": True})
                                mission_notice(nickname, mission_name)
                                print(f"{nickname}의 [{mission_name}] 미션 완료")
                    # ====================  [미션]  ===================
                
                # 결과 반영
                ref_weapon.update(weapon_stats)    

            # 웹후크 전송
            WEBHOOK_URL = DISCORD_ENHANCE_WEBHOOK_URL

            embed_color = 0x00FF00 if success else 0xFF0000
            status_text = "✅ **강화 성공!**" if success else "❌ **강화 실패**"
            used_items = []
            if use_polish:
                used_items.append("연마제")
                use_polish = False
            if use_high_polish:
                used_items.append("특수 연마제")
                use_high_polish = False

            embed_data = {
                "embeds": [
                    {
                        "title": status_text,
                        "color": embed_color,
                        "fields": [
                            {"name": "무기 이름", "value": f"`{weapon_data.get('이름','무기')}`", "inline": True},
                            {"name": "강화 종류", "value": enhance_type, "inline": True},
                            {"name": "현재 강화 수치", "value": f"{weapon_enhanced}강 ➜ {'{}강'.format(weapon_enhanced+1) if success else '{}강'.format(weapon_enhanced)}", "inline": True},
                            {"name": "사용한 아이템", "value": ', '.join(used_items) if used_items else "없음", "inline": False},
                            {"name": "성공 확률", "value": f"{enhancement_rate}%", "inline": True},
                        ],
                        "footer": {"text": "무기 강화 시스템"},
                    }
                ]
            }

            # 실제 전송
            try:
                requests.post(WEBHOOK_URL, json=embed_data)
            except Exception as webhook_error:
                print("Webhook Error:", webhook_error)
            return JsonResponse({'success': success})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
    
@csrf_exempt
def enhance_weapon_batch(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    try:
        body = json.loads(request.body)

        nickname = body.get('discord_username')
        enhance_type = body.get('enhanceType', '밸런스 강화')
        if isinstance(enhance_type, list):
            enhance_type = enhance_type[0]
        use_polish_limit = int(body.get('usePolishLimit', 0))
        use_high_polish_limit = int(body.get('useHighPolishLimit', 0))
        target_enhancement = int(body.get('targetEnhancement', 0))
        weapon_parts_limit = int(body.get('useWeaponPartsLimit', 0))

        # 강화 확률 테이블
        enhancement_probabilities = {
            0: 100, 1: 90, 2: 90, 3: 80, 4: 80, 5: 80,
            6: 70, 7: 60, 8: 60, 9: 40, 10: 40, 11: 30,
            12: 20, 13: 20, 14: 10, 15: 10, 16: 5, 17: 5,
            18: 3, 19: 1,
        }

        ref_weapon = db.reference(f"무기/유저/{nickname}")
        ref_item = db.reference(f"무기/아이템/{nickname}")
        weapon_data = ref_weapon.get() or {}
        item_data = ref_item.get() or {}

        current_enhancement = weapon_data.get("강화", 0)
        available_parts = item_data.get("강화재료", 0)
        available_polish = item_data.get("연마제", 0)
        available_high_polish = item_data.get("특수 연마제", 0)

        used_parts = used_polish = used_high_polish = 0
        logs = []

        # 1. 선차감 (트랜잭션)
        def reserve_materials(current):
            if current is None:
                raise Exception("인벤토리가 없습니다.")

            if current.get("강화재료", 0) < weapon_parts_limit:
                raise Exception("강화재료 부족")
            if current.get("연마제", 0) < use_polish_limit:
                raise Exception("연마제 부족")
            if current.get("특수 연마제", 0) < use_high_polish_limit:
                raise Exception("특수 연마제 부족")

            current["강화재료"] -= weapon_parts_limit
            current["연마제"] -= use_polish_limit
            current["특수 연마제"] -= use_high_polish_limit
            return current

        try:
            ref_item.transaction(reserve_materials)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
                
        weapon_stats = {k: v for k, v in weapon_data.items() if k not in ["강화", "이름", "강화내역"]}
        while (current_enhancement < target_enhancement and 
               used_parts < weapon_parts_limit and 
               available_parts - used_parts > 0):

            
            # 강화 준비
            enhancement_rate = enhancement_probabilities.get(current_enhancement, 0)
            use_polish = used_polish < use_polish_limit and (available_polish - used_polish) > 0
            use_high_polish = used_high_polish < use_high_polish_limit and (available_high_polish - used_high_polish) > 0

            if use_polish:
                enhancement_rate += 5
            if use_high_polish:
                enhancement_rate += 50

            roll = random.randint(1, 100)
            success = roll <= enhancement_rate

            used_parts += 1
            if use_polish: used_polish += 1
            if use_high_polish: used_high_polish += 1

            logs.append({
                "from": current_enhancement,
                "to": current_enhancement + 1 if success else current_enhancement,
                "success": success,
                "used_parts": 1,
                "used_polish": 1 if use_polish else 0,
                "used_high_polish": 1 if use_high_polish else 0,
                "chance": enhancement_rate,
            })

            
            if success:
                current_enhancement += 1
                # 스탯 적용 로직 (기존 enhance_weapon에서 그대로 가져오기)
                ref_weapon_log = db.reference(f"무기/유저/{nickname}/강화내역")
                weapon_log_data = ref_weapon_log.get() or {}
                current_stat_log = weapon_log_data.get(enhance_type, 0)
                ref_weapon_log.update({enhance_type: current_stat_log + 1})
                
                enhancement_options = db.reference(f"무기/강화").get() or {}
                stats = enhancement_options.get(enhance_type, "밸런스 강화")["stats"]

                for stat, base_increase in stats.items():
                    increase = base_increase
                    final = weapon_stats.get(stat, 0) + increase
                    weapon_stats[stat] = final

        # 로그 집계
        success_count = sum(1 for log in logs if log["success"])
        attempt_count = len(logs)

        # 최종 강화 수치 및 인벤토리 반영
        ref_weapon.update({"강화": current_enhancement})
        if success_count > 0 and weapon_stats: # 강화 성공했을 경우에만
            ref_weapon.update(weapon_stats)
        ref_item.update({
            "강화재료": max(available_parts - used_parts, 0),
            "연마제": max(available_polish - used_polish, 0),
            "특수 연마제": max(available_high_polish - used_high_polish, 0),
        })

        used_items_text = []
        if used_parts: used_items_text.append(f"강화재료 {used_parts}개")
        if used_polish: used_items_text.append(f"연마제 {used_polish}개")
        if used_high_polish: used_items_text.append(f"특수 연마제 {used_high_polish}개")

        previous_enhancement = weapon_data.get('강화', 0)
        ref_weapon = db.reference(f"무기/유저/{nickname}")
        weapon_data = ref_weapon.get() or {}
        # 웹훅 임베드 구성
        embed_data = {
            "embeds": [
                {
                    "title": f"✅ {nickname}님의 연속 강화 결과",
                    "color": 0x00ff00,
                    "fields": [
                        {"name": "무기 이름", "value": f"`{weapon_data.get('이름','무기')}`", "inline": True},
                        {"name": "강화 종류", "value": enhance_type, "inline": True},
                        {"name": "강화 수치 변화", "value": f"{weapon_data.get('강화', 0) - success_count}강 ➜ {weapon_data.get('강화', 0)}강", "inline": True},
                        {"name": "사용한 아이템", "value": ', '.join(used_items_text) if used_items_text else "없음", "inline": False},
                        {"name": "성공 횟수 / 시도 횟수", "value": f"{success_count} / {attempt_count}", "inline": True},
                    ],
                    "footer": {"text": "무기 강화 시스템"},
                }
            ]
        }

        # ====================  [미션]  ====================
        # 시즌미션 : 연마(무기 20강 달성)
        weapon_enhanced = weapon_data.get('강화', 0)
        if weapon_enhanced == 20:
            ref_mission = db.reference(f"미션/미션진행상태/{nickname}/시즌미션/연마")
            mission_data = ref_mission.get() or {}
            mission_bool = mission_data.get('완료',False)
            if not mission_bool:
                ref_mission.update({"완료": True})
                mission_notice(nickname,"연마")
                print(f"{nickname}의 [연마] 미션 완료")
        # ====================  [미션]  ====================

        # ====================  [미션]  ====================
        # 시즌미션 : 6종의 인장 미션
        weapon_enhanced = weapon_data.get('강화', 0)
        if weapon_enhanced == 20:
            ref_enhance = db.reference(f"무기/유저/{nickname}/강화내역")
            ref_inherit = db.reference(f"무기/유저/{nickname}/계승 내역/추가강화")
            
            enhance_data = ref_enhance.get() or {}
            inherit_data = ref_inherit.get() or {}

            # 시즌미션 이름 매핑: {강화이름: 미션명}
            mission_targets = {
                "공격 강화": "맹공",
                "스킬 강화": "현자",
                "명중 강화": "집중",
                "속도 강화": "신속",
                "방어 강화": "경화",
                "밸런스 강화": "균형"
            }

            for stat_name, mission_name in mission_targets.items():
                total = enhance_data.get(stat_name, 0)
                inherited = inherit_data.get(stat_name, 0)
                actual = total - inherited

                if actual == 20:
                    ref_mission = db.reference(f"미션/미션진행상태/{nickname}/시즌미션/{mission_name}")
                    mission_data = ref_mission.get() or {}
                    if not mission_data.get("완료", False):
                        ref_mission.update({"완료": True})
                        mission_notice(nickname, mission_name)
                        print(f"{nickname}의 [{mission_name}] 미션 완료")
            # ====================  [미션]  ===================
        # 실제 전송
        try:
            requests.post(DISCORD_ENHANCE_WEBHOOK_URL, json=embed_data)
        except Exception as webhook_error:
            print("Webhook Error:", webhook_error)


        def format_logs(logs):
            formatted_logs = []
            if not logs:
                return formatted_logs

            current = {
                "from": logs[0]["from"],
                "to": logs[0]["to"],
                "count": 0,
                "used_parts": 0,
                "used_polish": 0,
                "used_high_polish": 0,
                "success": False,
            }

            for i, log in enumerate(logs):
                # 같은 강화 목표면 누적
                if log["from"] == current["from"] and log["to"] == current["to"]:
                    current["count"] += 1
                    current["used_parts"] += log["used_parts"]
                    current["used_polish"] += log["used_polish"]
                    current["used_high_polish"] += log["used_high_polish"]
                    current["success"] = log["success"]  # 항상 마지막 결과로 갱신
                else:
                    # 이전 결과 정리
                    message = f"{current['from']}강 → {current['to']}강 {'성공 🎉' if current['success'] else '실패 ❌'}"
                    if current["count"] > 1:
                        message += f" ({current['count']}회 시도)"
                    costs = {
                        "강화재료": current["used_parts"],
                        "연마제": current["used_polish"],
                        "특수 연마제": current["used_high_polish"],
                    }
                    formatted_logs.append({"message": message, "costs": costs})

                    # 새 로그 시작
                    current = {
                        "from": log["from"],
                        "to": log["to"],
                        "count": 1,
                        "used_parts": log["used_parts"],
                        "used_polish": log["used_polish"],
                        "used_high_polish": log["used_high_polish"],
                        "success": log["success"],
                    }

            # 마지막 강화 결과 추가
            message = f"{current['from']}강 → {current['to']}강 {'성공 🎉' if current['success'] else '실패 ❌'}"
            if current["count"] > 1:
                message += f" ({current['count']}회 시도)"
            costs = {
                "강화재료": current["used_parts"],
                "연마제": current["used_polish"],
                "특수 연마제": current["used_high_polish"],
            }
            formatted_logs.append({"message": message, "costs": costs})

            return formatted_logs

        # 로그 포맷팅
        formatted_logs = format_logs(logs)

        return JsonResponse({
            "result": f"{weapon_data.get('이름', '무기')} {previous_enhancement}강 → {current_enhancement}강",
            "used": {
                "강화재료": used_parts,
                "연마제": used_polish,
                "특수 연마제": used_high_polish,
            },
            "logs": formatted_logs
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@csrf_exempt
def inherit_weapon(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        selected_weapon = data.get('selectedWeapon')
        new_weapon_name = data.get('newWeaponName')
        
        user = request.user  # ✅ 여기가 핵심! 로그인한 유저 정보 자동 제공
        
        # 예: 유저의 무기 데이터 확인 및 계승 처리
        print(f"{user.username}이(가) {selected_weapon}을(를) {new_weapon_name}(으)로 계승 요청")

        chance = random.random()  # 0 ~ 1 사이 랜덤 값

        if chance < 0.7:
            inherit_type = "기본 스탯 증가"
        else:
            inherit_type = "기본 스킬 레벨 증가"

        # inherit = weapon_data.get("계승", 0)
        # inherit_log = weapon_data.get("계승 내역", {})

        # # 🔹 기존 계승 내역 업데이트
        # if inherit_type in inherit_log:
        #     inherit_log[inherit_type] += 1
        # else:
        #     inherit_log[inherit_type] = 1

        # # 🔹 강화 내역 가져오기
        # nickname = interaction.user.name

        # ref_enhancement_log = db.reference(f"무기/유저/{nickname}/강화내역")
        # enhancement_log = ref_enhancement_log.get() or {}

        # selected_options = []
        # # 🔹 15강 이상이면 계승할 강화 옵션 선택
        # current_upgrade_level = self.weapon_data.get("강화", 0)
        # if current_upgrade_level > 15:
        #     num_inherit_upgrades = current_upgrade_level - 15
        #     weighted_options = []

        #     for option, count in enhancement_log.items():
        #         # 계승 가능 횟수만큼 옵션을 리스트에 추가 (가중치 방식)
        #         weighted_options.extend([option] * count)

        #     while len(selected_options) < num_inherit_upgrades and weighted_options:
        #         option = random.choice(weighted_options)

        #         # 해당 옵션의 계승 횟수가 제한보다 작으면 선택
        #         if selected_options.count(option) < enhancement_log[option]:
        #             selected_options.append(option)

        #             # 이미 선택한 만큼 weighted_options에서도 줄여줘야 중복 방지
        #             weighted_options.remove(option)
        #         else:
        #             # 만약 최대 횟수까지 이미 선택된 경우, 더는 뽑히지 않게
        #             weighted_options = [o for o in weighted_options if o != option]

        #     # 🔹 계승 내역에 추가
        #     for option in selected_options:
        #         # "추가강화" 키가 계승 내역에 존재하는지 확인하고 없으면 생성
        #         if "추가강화" not in inherit_log:
        #             inherit_log["추가강화"] = {}  # "추가강화"가 없다면 새로 생성

        #         # 해당 옵션이 추가강화 내역에 있는지 확인
        #         if option in inherit_log["추가강화"]:
        #             inherit_log["추가강화"][option] += 1  # 이미 있다면 개수 증가
        #         else:
        #             inherit_log["추가강화"][option] = 1  # 없으면 1로 시작

        # ref_weapon_base = db.reference(f"무기/기본 스탯")
        # base_weapon_stats = ref_weapon_base.get() or {}

        # base_stat_increase = inherit_log.get("기본 스탯 증가", 0) * 0.3
        # base_weapon_stat = base_weapon_stats[self.selected_weapon_type]

        # # 계승 내역에 각 강화 유형을 추가
        # enhanced_stats = {}

        # ref_weapon_enhance = db.reference(f"무기/강화")
        # enhancement_options = ref_weapon_enhance.get() or {}
        # # 계승 내역에서 각 강화 옵션을 확인하고, 해당 스탯을 강화 내역에 추가
        # for enhancement_type, enhancement_data in inherit_log.items():
        #     if enhancement_type == "추가강화":  # 추가강화 항목만 따로 처리
        #         # "추가강화" 내역에서 각 강화 옵션을 확인
        #         for option, enhancement_count in enhancement_data.items():
        #             # 해당 옵션에 대한 stats를 업데이트
        #             if option in enhancement_options:
        #                 stats = enhancement_options[option]["stats"]
        #                 # 강화된 수치를 적용
        #                 for stat, increment in stats.items():
        #                     if stat in enhanced_stats:
        #                         enhanced_stats[stat] += increment * enhancement_count  # 강화 내역 수 만큼 적용
        #                     else:
        #                         enhanced_stats[stat] = increment * enhancement_count  # 처음 추가되는 stat은 그 값으로 설정

        # new_enhancement_log = dict(Counter(selected_options))

        # # 메시지 템플릿에 추가된 강화 내역을 포함
        # enhancement_message = "\n강화 내역:\n"
        # for option, count in new_enhancement_log.items():
        #     enhancement_message += f"{option}: {count}회\n"

        # if "추가강화" in inherit_log:
        #     new_enhancement_log = Counter(inherit_log["추가강화"])  # 기존 내역 추가
        
        # basic_skill_levelup = inherit_log.get("기본 스킬 레벨 증가", 0)
        
        # basic_skills = ["속사", "기습", "강타", "헤드샷", "창격", "수확", "명상", "화염 마법", "냉기 마법", "신성 마법", "일섬"]
        # skills = base_weapon_stat["스킬"]
        # for skill_name in basic_skills:
        #     if skill_name in skills:
        #         skills[skill_name]["레벨"] += basic_skill_levelup

        # new_weapon_data = {
        #     "강화": 0,  # 기본 강화 값
        #     "계승": inherit + 1,
        #     "이름": new_weapon_name,
        #     "무기타입": self.selected_weapon_type,
        #     "공격력": base_weapon_stat["공격력"] + round(base_weapon_stat["공격력"] * base_stat_increase + enhanced_stats.get("공격력", 0)),
        #     "스킬 증폭": base_weapon_stat["스킬 증폭"] + round(base_weapon_stat["스킬 증폭"] * base_stat_increase + enhanced_stats.get("스킬 증폭", 0)),
        #     "내구도": base_weapon_stat["내구도"] + round(base_weapon_stat["내구도"] * base_stat_increase + enhanced_stats.get("내구도", 0)),
        #     "방어력": base_weapon_stat["방어력"] + round(base_weapon_stat["방어력"] * base_stat_increase + enhanced_stats.get("방어력", 0)),
        #     "스피드": base_weapon_stat["스피드"] + round(base_weapon_stat["스피드"] * base_stat_increase + enhanced_stats.get("스피드", 0)),
        #     "명중": base_weapon_stat["명중"] + round(base_weapon_stat["명중"] * base_stat_increase + enhanced_stats.get("명중", 0)),
        #     "치명타 대미지": base_weapon_stat["치명타 대미지"] + enhanced_stats.get("치명타 대미지", 0),
        #     "치명타 확률": base_weapon_stat["치명타 확률"] + enhanced_stats.get("치명타 확률", 0),
        #     "스킬": skills,
        #     "강화내역": new_enhancement_log,
        #     "계승 내역": inherit_log 
        # }

        # ref_weapon = db.reference(f"무기/유저/{nickname}")
        # ref_weapon.update(new_weapon_data)

        # await interaction.response.send_message(
        #     f"[{self.weapon_data.get('이름', '이전 무기')}]의 힘을 계승한 **[{new_weapon_name}](🌟 +{inherit + 1})** 무기가 생성되었습니다!\n"
        #     f"계승 타입: [{self.inherit_type}] 계승이 적용되었습니다!\n"
        #     f"{enhancement_message}" 
        # )
        # 로직 수행 후 결과 리턴
        return JsonResponse({
            'inherit_reward': inherit_type,
            'inherit_additional_enhance': { '공격 강화': 3 }
        })

def get_skill_params(request, discord_username):
    skill_name = request.GET.get('key')  # 프론트엔드에서 보내는 skill_tooltip_xxx

    if not skill_name:
        return JsonResponse({'error': 'No key provided'}, status=400)

    ref_weapon_stats = db.reference(f"무기/유저/{discord_username}")
    weapon_stats_data = ref_weapon_stats.get() or {}

    response_context = {}

    ref_skill_data = db.reference(f"무기/스킬/{skill_name}")
    skill_server_data = ref_skill_data.get() or {}
    values = skill_server_data.get('values', {})
    cooldown = skill_server_data.get('cooldown', {})
    level = 1

    template_context = {
        **values,
        **cooldown,
        '레벨': level,
        '공격력': weapon_stats_data.get('공격력', 0),
        '스킬_증폭': weapon_stats_data.get('스킬 증폭', 0),
        '명중': weapon_stats_data.get('명중', 0),
        '스피드': weapon_stats_data.get('스피드', 0),
        '내구도': weapon_stats_data.get('내구도', 0),
        '방어력': weapon_stats_data.get('방어력', 0),
        '치명타_확률': weapon_stats_data.get('치명타 확률', 0),
        '치명타_대미지': weapon_stats_data.get('치명타 대미지', 0),
    }

    response_context = template_context

    return JsonResponse(response_context)

def get_skills_with_tooltips(request):
    ref = db.reference("무기/스킬")
    all_skills = ref.get() or {}

    result = []

    for skill_name, skill_info in all_skills.items():
        tooltip_key = skill_info.get('tooltip')
        if tooltip_key and tooltip_key.startswith("skill_tooltip_"):
            result.append({
                'skill_name': skill_name,
                'tooltip_key': tooltip_key,
                'display_name': tooltip_key.replace('skill_tooltip_', '')  # 보기 좋게
            })

    return JsonResponse(result, safe=False)