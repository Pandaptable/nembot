import aiohttp
import random

from config import *
from globals import server, ui_instance

LAST_DEATH_COUNT = 3621


async def check_death():
	global LAST_DEATH_COUNT
	global CLIENT_STEAM_ID
	CLIENT_STEAM_ID = server.get_info("provider", "steamid")
	CURRENT_DEATH_COUNT = int(server.get_info("player", "match_stats", "deaths"))
	if server.get_info("player", "steamid") == CLIENT_STEAM_ID:
		if LAST_DEATH_COUNT == 3621:
			LAST_DEATH_COUNT = CURRENT_DEATH_COUNT
		if CURRENT_DEATH_COUNT < LAST_DEATH_COUNT:
			LAST_DEATH_COUNT = 0
		if CURRENT_DEATH_COUNT > LAST_DEATH_COUNT:
			LAST_DEATH_COUNT = CURRENT_DEATH_COUNT
			if server.get_info("map", "phase") == "live":
				await on_death()


async def on_death():
	if OPENSHOCK_ENABLED:
		if OPENSHOCK_PUNISHMENT_TYPE == "random":
			shocker_list = [random.choice(OPENSHOCK_SHOCKER_LIST)]
		elif OPENSHOCK_PUNISHMENT_TYPE == "one":
			shocker_list = [OPENSHOCK_SHOCKER_LIST[0]]
		else:
			shocker_list = OPENSHOCK_SHOCKER_LIST

		intensity = random.randint(*OPENSHOCK_STRENGTH_RANGE)
		duration = (random.randint(*OPENSHOCK_DURATION_RANGE) // 100) * 100

		shocks = [
			{
				"id": shock_id,
				"type": OPENSHOCK_TYPE,
				"intensity": intensity,
				"duration": duration,
			}
			for shock_id in shocker_list
		]

		payload = {"shocks": shocks, "customName": "Died in CS"}

		async with aiohttp.ClientSession() as session:
			try:
				async with session.post(
					OPENSHOCK_API_URL,
					json=payload,
					headers={"OpenShockToken": OPENSHOCK_API_TOKEN},
				) as response:
					if response.status == 200:
						ui_instance.update_status("Sent shock" + ("s" if OPENSHOCK_PUNISHMENT_TYPE == "all" else f": {intensity} for {duration / 1000}s"))
						print("Shock" + ("s" if OPENSHOCK_PUNISHMENT_TYPE == "all" else "") + " sent successfully.")
					else:
						print(f"Failed to activate shocker. Response: {response}")
			except aiohttp.ClientError as e:
				print(f"An error occurred: {e}")


async def check_if_dead() -> bool:
	global DEAD_STATUS
	if server.get_info("player", "steamid") != server.get_info("provider", "steamid") or server.get_info("player", "state", "health") <= 0:
		DEAD_STATUS = True
	else:
		DEAD_STATUS = False
	return DEAD_STATUS
