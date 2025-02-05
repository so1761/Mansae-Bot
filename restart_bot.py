import subprocess
import os
import signal
import aiohttp
import asyncio
from dotenv import load_dotenv

API_KEY = None
JIMO_PUUID = None
MELON_PUUID = None



async def nowgame(puuid):
    url = f'https://kr.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}'
    headers = {'X-Riot-Token': API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if (data["gameMode"] == "CLASSIC" and 
                    data["gameType"] == "MATCHED" and 
                    data["gameQueueConfigId"] == 420):
                    return True
                else:
                    return False
            else:
                return False
            
def find_and_kill_bot(process_name="bot2.py"):
    try:
        # 현재 실행 중인 프로세스 중 bot2.py 찾기
        result = subprocess.run(["ps", "-ef"], stdout=subprocess.PIPE, text=True)
        processes = result.stdout.splitlines()
        
        # bot2.py 관련 프로세스 필터링
        for process in processes:
            if process_name in process and "grep" not in process:
                # 프로세스 ID 추출 (2번째 열에 PID 있음)
                pid = int(process.split()[1])
                print(f"Found process '{process_name}' with PID: {pid}")

                # 프로세스 종료
                os.kill(pid, signal.SIGKILL)
                print(f"Process '{process_name}' with PID {pid} killed.")
                return True
        print(f"No process named '{process_name}' found.")
        return False
    except Exception as e:
        print(f"Error while killing process: {e}")
        return False

def restart_bot(script_name="bot2.py"):
    try:
        # nohup으로 bot2.py 재시작
        command = f"nohup python -u {script_name} >> nohup.out 2>&1 &"
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"Script '{script_name}' restarted successfully.")
    except Exception as e:
        print(f"Error while restarting script: {e}")

async def main():
    load_dotenv()

    API_KEY = os.getenv("RIOT_API_KEY")
    JIMO_PUUID = os.getenv("JIMO_PUUID")
    MELON_PUUID = os.getenv("MELON_PUUID")

    jimo_game = await nowgame(JIMO_PUUID)
    melon_game = await nowgame(MELON_PUUID)
    if not jimo_game and not melon_game:
        if find_and_kill_bot("bot2.py"):
            restart_bot("bot2.py")
        else:
            print("No process to kill. Starting a new one.")
            restart_bot("bot2.py")
    else:
        print("지모와 멜론이 게임중입니다. 재부팅을 하지 않습니다")

if __name__ == "__main__":
    asyncio.run(main())