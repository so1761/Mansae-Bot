# 예시 코드
from PIL import Image, ImageDraw, ImageFont

# 전투 필드 이미지 생성 (간단한 예시)
img = Image.new('RGB', (200, 200), color='white')
d = ImageDraw.Draw(img)

# 플레이어 위치 그리기 (예시)
d.rectangle([50, 50, 70, 70], fill="blue")  # 플레이어 A
d.rectangle([150, 50, 170, 70], fill="red")  # 플레이어 B

# 이미지 저장 또는 메시지로 전송
img.save('battle_field.png')