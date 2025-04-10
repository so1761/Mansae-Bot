from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    global_name = models.CharField(max_length=150, blank=True, null=True)  # 닉네임
    avatar = models.CharField(max_length=255, blank=True, null=True)
    avatar_url = models.CharField(max_length=255, blank=True, null=True)
    discord_username = models.CharField(max_length=150, blank=True, null=True)  # 닉네임

class Weapon(models.Model):
    name = models.CharField(max_length=100)
    weapon_type = models.CharField(max_length=50)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # ⚙️ 기본 스탯
    base_attack_power = models.IntegerField(default=0)
    base_durability = models.IntegerField(default=0)
    base_accuracy = models.IntegerField(default=0)
    base_defense = models.IntegerField(default=0)
    base_range = models.IntegerField(default=0)
    base_speed = models.IntegerField(default=0)
    base_skill_enhance = models.IntegerField(default=0)
    base_critical_damage = models.FloatField(default=1.5)
    base_critical_hit_chance = models.FloatField(default=0.05)

    # 📈 계승 스탯 증가
    base_increase_attack_power = models.IntegerField(default=0)
    base_increase_durability = models.IntegerField(default=0)
    base_increase_accuracy = models.IntegerField(default=0)
    base_increase_defense = models.IntegerField(default=0)
    base_increase_speed = models.IntegerField(default=0)
    base_increase_skill_enhance = models.IntegerField(default=0)

    # 🛠 강화 수치
    enhanced_attack_power = models.FloatField(default=0)
    enhanced_durability = models.FloatField(default=0)
    enhanced_accuracy = models.FloatField(default=0)
    enhanced_defense = models.FloatField(default=0)
    enhanced_speed = models.FloatField(default=0)
    enhanced_skill_enhance = models.FloatField(default=0)
    enhanced_critical_damage = models.FloatField(default=0)
    enhanced_critical_hit_chance = models.FloatField(default=0)

    # 💥 최종 스탯
    total_attack_power = models.FloatField(default=0)
    total_durability = models.FloatField(default=0)
    total_accuracy = models.FloatField(default=0)
    total_defense = models.FloatField(default=0)
    total_speed = models.FloatField(default=0)
    total_skill_enhance = models.FloatField(default=0)
    total_critical_damage = models.FloatField(default=0)
    total_critical_hit_chance = models.FloatField(default=0)

    def get_inheritance_value(self, stat_name):
        return getattr(self, f"base_increase_{stat_name}", 0)

    def get_enhancement_value(self, stat_name):
        return getattr(self, f"enhanced_{stat_name}", 0)

    def calculate_total_stats(self):
        self.total_attack_power = (
            self.base_attack_power +
            self.base_increase_attack_power +
            self.enhanced_attack_power
        )
        self.total_durability = (
            self.base_durability +
            self.base_increase_durability +
            self.enhanced_durability
        )
        self.total_accuracy = (
            self.base_accuracy +
            self.base_increase_accuracy +
            self.enhanced_accuracy
        )
        self.total_defense = (
            self.base_defense +
            self.base_increase_defense +
            self.enhanced_defense
        )
        self.total_speed = (
            self.base_speed +
            self.base_increase_speed +
            self.enhanced_speed
        )
        self.total_skill_enhance = (
            self.base_skill_enhance +
            self.base_increase_skill_enhance +
            self.enhanced_skill_enhance
        )
        self.total_critical_damage = (
            self.base_critical_damage +
            self.enhanced_critical_damage
        )
        self.total_critical_hit_chance = (
            self.base_critical_hit_chance +
            self.enhanced_critical_hit_chance
        )

    def save(self, *args, **kwargs):
        self.calculate_total_stats()  # 저장 전에 자동 계산
        super().save(*args, **kwargs)
        

    def __str__(self):
        return self.name

    

class Enhancement(models.Model):
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE, related_name='enhancements')  # 해당 무기

    attack_enhance = models.IntegerField(default=0)  # 공격력 강화
    durability_enhance = models.IntegerField(default=0)  # 내구도 강화
    accuracy_enhance = models.IntegerField(default=0)  # 명중 강화
    speed_enhance = models.IntegerField(default=0)  # 속도 강화
    defense_enhance = models.IntegerField(default=0)  # 방어력 강화
    skill_enhance = models.IntegerField(default=0)  # 스킬 증폭 강화
    critical_damage_enhance = models.IntegerField(default=0)  # 치명타 대미지 강화
    critical_hit_chance_enhance = models.IntegerField(default=0)  # 치명타 확률 강화
    balance_enhance = models.IntegerField(default=0)  # 밸런스 강화

    enhancement_level = models.IntegerField(default=0)  # 강화 레벨
    enhancement_date = models.DateTimeField(auto_now_add=True)  # 강화된 날짜

    def __str__(self):
        return f"Enhancement Level {self.enhancement_level} for {self.weapon.name}"

class Inheritance(models.Model):
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE, related_name='inheritances')  # 해당 무기
    base_stat_increase = models.IntegerField(default=0)  # 기본 스탯 증가
    base_skill_level_increase = models.IntegerField(default=0) # 기본 스킬 레벨 증가
    additional_enhance = models.JSONField(default=dict)  # 추가 강화 (공격 강화, 내구도 강화 등)
    inheritance_level = models.IntegerField(default=0)  # 계승 레벨
    inheritance_date = models.DateTimeField(auto_now_add=True)  # 계승된 날짜

    def __str__(self):
        return f"Inheritance for {self.weapon.name}"

class Skill(models.Model):
    weapon = models.ForeignKey(Weapon, on_delete=models.CASCADE, related_name='skills')  # 해당 무기
    skill_name = models.CharField(max_length=50)  # 스킬 이름 (예: 창격)
    level = models.IntegerField(default=0)  # 스킬 레벨
    cooldown = models.IntegerField(default=0)  # 전체 쿨타임
    current_cooldown = models.IntegerField(default=0)  # 현재 쿨타임

    def __str__(self):
        return f"Skill: {self.skill_name} for {self.weapon.name}"