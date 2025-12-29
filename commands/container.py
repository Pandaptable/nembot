import asyncio
import json
import random

import aiohttp
from thefuzz import process

from command_execution import execute_command
from config import PREFIX
from database import insert_item
from globals import TEAMS


class Wear:
	SFUI_InvTooltip_Wear_Amount_0 = {
		"name": "Factory New",
		"database_id": "SFUI_InvTooltip_Wear_Amount_0",
		"min_float": 0,
		"max_float": 0.07,
	}
	SFUI_InvTooltip_Wear_Amount_1 = {
		"name": "Minimal Wear",
		"database_id": "SFUI_InvTooltip_Wear_Amount_1",
		"min_float": 0.07,
		"max_float": 0.15,
	}
	SFUI_InvTooltip_Wear_Amount_2 = {
		"name": "Field-Tested",
		"database_id": "SFUI_InvTooltip_Wear_Amount_2",
		"min_float": 0.15,
		"max_float": 0.38,
	}
	SFUI_InvTooltip_Wear_Amount_3 = {
		"name": "Well-Worn",
		"database_id": "SFUI_InvTooltip_Wear_Amount_3",
		"min_float": 0.38,
		"max_float": 0.45,
	}
	SFUI_InvTooltip_Wear_Amount_4 = {
		"name": "Battle-Scarred",
		"database_id": "SFUI_InvTooltip_Wear_Amount_4",
		"min_float": 0.45,
		"max_float": 1,
	}


async def open_container(container_name_user, username, steamid, team, cmd, container_type_user):
	if not container_name_user:
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} No container name provided.. Usage: {cmd} <name> or random")
		else:
			await execute_command(f"say {PREFIX} No container name provided. Usage: {cmd} <name> or random")
		return
	containers = await load_containers()
	if container_name_user == "random":
		container_name_user = random.choice([container["name"] for container in containers])
	# fuzzy search for container
	container_matches = process.extract(container_name_user, [container["name"] for container in containers], limit=None)
	# remove results that don't contain all words present in container_name
	filtered_matches = [name for name in container_matches if all(word.lower() in name[0].lower() for word in container_name_user.lower().split())]
	if not filtered_matches:
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} No matching containers found for {container_name_user}.")
		else:
			await execute_command(f"say {PREFIX} No matching containers found for {container_name_user}.")
		return
	matched_containers = [container for container in containers if container["name"] in [match[0] for match in filtered_matches]]
	proper_container_name = matched_containers[0]["name"]
	container_type = matched_containers[0]["type"]
	if container_type_user == "capsule":
		while container_type not in ["Sticker Capsule", "Autograph Capsule"]:
			container_name_user = random.choice([container["name"] for container in containers if container["type"] in ["Sticker Capsule", "Autograph Capsule"]])
			matched_containers = [container for container in containers if container["name"] == container_name_user]
			proper_container_name = matched_containers[0]["name"]
			container_type = matched_containers[0]["type"]
	elif container_type_user == "case":
		while container_type not in ["Case"]:
			container_name_user = random.choice([container["name"] for container in containers if container["type"] == "Case"])
			matched_containers = [container for container in containers if container["name"] == container_name_user]
			proper_container_name = matched_containers[0]["name"]
			container_type = matched_containers[0]["type"]
	container_name = matched_containers[0]["name"]
	# search through contains list to get all rarities available in a case, if contains_rare list also exists then add gold to rarity list
	contains = matched_containers[0]["contains"]
	rarity_list = []
	for item in contains:
		rarity_id = item["rarity"]["id"].replace("_weapon", "")
		if (
			any(rarity_id.startswith(prefix) for prefix in ["rarity_common", "rarity_uncommon", "rarity_rare", "rarity_mythical", "rarity_legendary", "rarity_ancient"])
			and rarity_id not in rarity_list
		):
			rarity_list.append(rarity_id)
	if matched_containers[0]["contains_rare"] and "gold" not in rarity_list:
		rarity_list.append("gold")
	# Find the entry in odds.json that includes ALL rarities in rarity_list
	rarity_set = set(rarity_list)
	for odds in load_odds():
		container_rarity_ids = {rarity["id"] for rarity in odds["rarities"]}
		if container_rarity_ids == rarity_set:
			mapped_odds = odds
			break
	else:
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} You tried to open {proper_container_name} but my code is shit so it broke </3.")
		else:
			await execute_command(f"say {PREFIX} You tried to open {proper_container_name} but my code is shit so it broke </3.")
		print(f"{proper_container_name} tried to open by {username}, no odds mapping was able to be made.")
		return

	rarity_counts = {}
	for item in matched_containers[0]["contains"]:
		rid = item["rarity"]["id"].replace("_weapon", "")
		rarity_counts[rid] = rarity_counts.get(rid, 0) + 1

	if matched_containers[0].get("contains_rare", []):
		rarity_counts["gold"] = len(matched_containers[0].get("contains_rare", []))

	rarity_odds = {r["id"]: r["odds"] for r in mapped_odds["rarities"]}

	item_pool = []
	weights = []

	for item in matched_containers[0]["contains"]:
		rid = item["rarity"]["id"].replace("_weapon", "")
		base_odds = rarity_odds.get(rid, 0)
		count_in_rarity = rarity_counts[rid]
		item_weight = base_odds / count_in_rarity
		item_pool.append(item)
		weights.append(item_weight)

	for item in matched_containers[0]["contains_rare"]:
		base_odds = rarity_odds.get("gold", 0)
		count_in_rarity = rarity_counts["gold"]
		item_weight = base_odds / count_in_rarity
		item_pool.append(item)
		weights.append(item_weight)

	chosen_item = random.choices(item_pool, weights=weights, k=1)[0]
	if container_type in ["Sticker Capsule", "Autograph Capsule"]:
		skin_list = await load_stickers()
	else:
		skin_list = await load_skins()
	item_json = [skin for skin in skin_list if skin["id"] == chosen_item["id"]]
	if not item_json:
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} You tried to open {proper_container_name} but my code is shit so it broke </3.")
		else:
			await execute_command(f"say {PREFIX} You tried to open {proper_container_name} but my code is shit so it broke </3.")
		print(f"Container: {proper_container_name} | Chosen item: {chosen_item}")
		return
	item_name = item_json[0]["name"]
	item_rarity = item_json[0]["rarity"]["id"].replace("_weapon", "")
	# Determine float
	if container_type not in ["Sticker Capsule", "Autograph Capsule"]:
		skin_min_float = item_json[0]["min_float"]
		skin_max_float = item_json[0]["max_float"]
		skin_float = random.uniform(skin_min_float, skin_max_float)
		displayed_float = float("{:.9f}".format(skin_float))
		# Determine wear name based on float
		wear_name = None
		for attr in dir(Wear):
			if attr.startswith("SFUI_InvTooltip_Wear_Amount_"):
				wear_data = getattr(Wear, attr)
				if wear_data["min_float"] <= displayed_float <= wear_data["max_float"]:
					wear_name = wear_data["name"]
					break
		# Determine stattrak
		skin_stattrak = False
		skin_stattrak = item_json[0]["stattrak"] and random.random() < 0.1
		# Determine pattern
		skin_pattern = random.randint(0, 1000)

		skin_opened = await format_skin(item_name, displayed_float, skin_pattern, skin_stattrak, username)
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} {skin_opened}")
		else:
			await execute_command(f"say {PREFIX} {skin_opened}")
	else:
		skin_pattern = None
		skin_float = None
		displayed_float = None
		wear_name = None
		skin_stattrak = False

		skin_opened = await format_sticker(item_name, username)
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} {skin_opened}")
		else:
			await execute_command(f"say {PREFIX} {skin_opened}")

	await insert_item(container_name, item_name, item_rarity, skin_pattern, skin_float, wear_name, skin_stattrak, username, steamid)

	return


async def format_skin(skin_name: str, float: float, pattern: int, stattrak: bool, username: str) -> str:
	if stattrak:
		if "★" in skin_name:
			return f"{username} has found: ★ StatTrak™ {skin_name} | {pattern} | {float}f"
		else:
			return f"{username} has found: StatTrak™ {skin_name} | {pattern} | {float}"
	else:
		return f"{username} has found: {skin_name} | {pattern} | {float}"


async def format_sticker(sticker_name: str, username: str) -> str:
	return f"{username} has found: {sticker_name}"


async def load_containers() -> dict:
	async with aiohttp.ClientSession() as session:
		async with session.get("https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/crates.json") as response:
			if response.status == 200:
				data = json.loads(await response.text())
			else:
				raise Exception(f"Error: {response.status}")
	return data


async def load_skins() -> dict:
	async with aiohttp.ClientSession() as session:
		async with session.get("https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json") as response:
			if response.status == 200:
				data = json.loads(await response.text())
			else:
				raise Exception(f"Error: {response.status}")
	return data


async def load_stickers() -> dict:
	async with aiohttp.ClientSession() as session:
		async with session.get("https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/stickers.json") as response:
			if response.status == 200:
				data = json.loads(await response.text())
			else:
				raise Exception(f"Error: {response.status}")
	return data


def load_odds() -> dict:
	with open("data/odds.json", "r") as f:
		data = json.load(f)
	return data
