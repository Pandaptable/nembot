import math
import os
import random
import re
from collections import defaultdict

from unit_parse import parser

from command_execution import execute_command
from config import PREFIX
from database import insert_fish, update_balance
from globals import TEAMS, server

loot_tables = {}


class Rarity:
	blue = {
		"name": "Blue",
		"odds": 79.92,
		"color": "",
		"database_id": "blue",
		"price_mult": 1.0,
	}
	purple = {
		"name": "Purple",
		"odds": 15.98,
		"color": "\r",
		"database_id": "purple",
		"price_mult": 1.8,
	}
	pink = {
		"name": "Pink",
		"odds": 3.2,
		"color": "",
		"database_id": "pink",
		"price_mult": 4.0,
	}
	red = {
		"name": "Red",
		"odds": 0.64,
		"color": "",
		"database_id": "red",
		"price_mult": 6.0,
	}
	gold = {
		"name": "Gold",
		"odds": 0.26,
		"color": "",
		"database_id": "gold",
		"price_mult": 10.0,
	}
	contraband = {
		"name": "Contraband",
		"odds": 0.0256,
		"color": "",
		"database_id": "contraband",
		"price_mult": 15.0,
	}

	@classmethod
	def getattr(cls, quality) -> dict:
		"""Retrieve rarity data dynamically by quality name."""
		if hasattr(cls, quality):
			return getattr(cls, quality)
		raise AttributeError(f"No such rarity: {quality}")


class Map:
	ar_baggage = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "ar_baggage",
	}
	ar_pool_day = {
		"tables_increased": ["lake"],
		"tables_excluded": [],
		"name": "ar_pool_day",
	}
	ar_shoots = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "ar_shoots",
	}
	cs_italy = {
		"tables_increased": ["lake"],
		"tables_excluded": ["ocean"],
		"name": "cs_italy",
	}
	cs_office = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "cs_office",
	}
	de_ancient = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_ancient",
	}
	de_anubis = {
		"tables_increased": ["lake", "ocean"],
		"tables_excluded": [],
		"name": "de_anubis",
	}
	de_basalt = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_basalt",
	}
	de_dust2 = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_dust2",
	}
	de_edin = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_edin",
	}
	de_inferno = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_inferno",
	}
	de_mirage = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_mirage",
	}
	de_nuke = {
		"tables_increased": ["lake", "alien", "void", "rain"],
		"tables_excluded": ["ocean"],
		"name": "de_nuke",
	}
	de_overpass = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_overpass",
	}
	de_palais = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_palais",
	}
	de_train = {
		"tables_increased": ["rain"],
		"tables_excluded": [],
		"name": "de_train",
	}
	de_vertigo = {
		"tables_increased": ["lake", "water_trash", "metal"],
		"tables_excluded": [],
		"name": "de_vertigo",
	}
	de_whistle = {
		"tables_increased": [],
		"tables_excluded": [],
		"name": "de_whistle",
	}

	@classmethod
	def getattr(cls, map) -> dict | bool:
		"""Retrieve map data dynamically by map name."""
		if hasattr(cls, map):
			return getattr(cls, map)
		else:
			return False


async def cast_line(steamid: int, username: str, team: str):
	catches = 1
	bonus = False
	map = server.get_info("map", "name")

	fish_table_pre = [
		"lake",
		"ocean",
		"rain",
		"alien",
		"void",
		"water_trash",
		"metal",
	]

	if Map.getattr(map):
		if Map.getattr(map)["tables_increased"]:
			if random.randint(0, 100) <= 70:
				fish_table_pre = Map.getattr(map)["tables_increased"]

		if any(t in Map.getattr(map)["tables_excluded"] for t in fish_table_pre):
			fish_table_pre = [t for t in fish_table_pre if t not in Map.getattr(map)["tables_excluded"]]
	else:
		pass

	fish_table = random.choice(fish_table_pre)

	rod_cast_data = random.choice([
		"small",
		"sparkling",
		"large",
		"gold",
	])  # TODO: maybe implement double fish

	rolls = []

	for _ in range(3):
		roll = await roll_loot_table(fish_table)
		size_calc = await roll_item_size(roll)
		rolls.append([roll, size_calc])

	if rod_cast_data == "small":
		reroll_type = "small"
	if rod_cast_data == "sparkling":
		reroll_type = "tier"
	if rod_cast_data == "large":
		reroll_type = "large"
	if rod_cast_data == "gold":
		reroll_type = "rare"

	chosen = rolls[0]
	for roll in rolls:
		match reroll_type:
			case "none":
				chosen = roll
			case "small":
				if roll[1] < chosen[1]:
					chosen = roll
			case "large":
				if roll[1] > chosen[1]:
					chosen = roll
			case "tier":
				if roll[0]["tier"] > chosen[0]["tier"]:
					chosen = roll
			case "rare":
				if roll[0].get("rare"):
					chosen = roll

	fish_roll = chosen[0]
	size = chosen[1]

	quality = random.choices(
		[
			Rarity.blue,
			Rarity.purple,
			Rarity.pink,
			Rarity.red,
			Rarity.gold,
			Rarity.contraband,
		],
		weights=[
			79.92,
			15.98,
			3.2,
			0.64,
			0.26,
			0.0256,
		],
	)

	if rod_cast_data == "double" and random.random() < 0.15:
		catches = 2
		bonus = True

	for _ in range(catches):
		fish_name = fish_roll["item_name"]
		item_description = fish_roll["item_description"]
		catch_blurb = fish_roll["catch_blurb"]
		quality_name = quality[0]["name"]
		quality_color = quality[0]["color"]
		quality = quality[0]["database_id"]
		normalized_size = parser(f"{size} cm")
		price = await calculate_worth(fish_roll, quality, size)

		await insert_fish(fish_name, size, price, quality, steamid, username)
		await update_balance(steamid, price)
		if team in TEAMS:
			await execute_command(f"say_team {PREFIX} {username}: 〈͜͡˒ ⋊ You caught a {quality_name} {fish_name}! {catch_blurb} It's {normalized_size} and is worth ₶{price}!", 0.5)
		else:
			await execute_command(f"say {PREFIX} {username}: 〈͜͡˒ ⋊ You caught a {quality_name} {fish_name}! {catch_blurb} It's {normalized_size} and is worth ₶{price}!", 0.5)


async def calculate_worth(fish_roll: dict, quality: str, size: str) -> int:
	size_prefix = {
		0.1: 1.75,
		0.25: 0.6,
		0.5: 0.8,
		1.0: 1.0,
		1.5: 1.5,
		2.0: 2.5,
		3.0: 4.25,
	}

	average = fish_roll["average_size"]
	calc = size / average
	mult = 1.0

	for p in size_prefix.keys():
		if p > calc:
			break
		mult = size_prefix[p]

	idata = fish_roll

	value = idata["sell_value"]

	if not idata.get("generate_worth"):
		idata["generate_worth"] = True

	if idata["generate_worth"]:
		t = 1.0 + (0.25 * idata["tier"])
		w = idata["loot_weight"]
		value = pow(5 * t, 2.5 - w)

		if w < 0.4:
			value *= 1.1
		if w < 0.15:
			value *= 1.25
		if w < 0.05:
			value *= 1.5

	worth = math.ceil(value * mult * Rarity.getattr(quality)["price_mult"])

	return worth


async def generate_loot_tables(category: str, table: str):
	new_table = {"entries": {}, "total_weight": 0.0}
	total_weight = 0.0

	for item, data in item_data.items():
		if data["category"] == category and data["loot_table"] == table:
			total_weight += data["loot_weight"]
			new_table["entries"][item] = total_weight

	new_table["total_weight"] = total_weight
	loot_tables[table] = new_table
	print(f"Generated Table {table} for category {category}")


async def roll_loot_table(table, max_tier=-1) -> dict:
	table_data = loot_tables[table]

	for _ in range(20):
		roll = random.uniform(0.0, loot_tables[table]["total_weight"])
		for item, cumulative_weight in table_data["entries"].items():
			if cumulative_weight > roll:
				data = item_data[item]
				if max_tier == -1 or data["tier"] <= max_tier:
					return data


async def roll_item_size(item: str) -> float:
	average_size = item["average_size"]
	deviation = average_size * 0.55
	average_size += average_size * 0.25

	roll = await stepify(random.gauss(average_size, deviation), 0.01)
	roll = round(abs(roll), 2)
	return roll


async def stepify(value: float, step: float) -> float:
	return round(value / step) * step


max_depth = 8

resource_type_regex = re.compile(r"\[gd_resource.*\]")
ext_resource_regex = re.compile(r'\[ext_resource path="(.+)" type="(.+)" id=(\d+)\]')
resource_regex = re.compile(r"\[(resource)\]")
key_value_regex = re.compile(r"(\w+)\s*=\s*(.*)")

organized_items = {}
loot_table_items = defaultdict(dict)  # loot_table -> fishname -> data


async def parse_files_in_directory(directory_path: str, current_depth: int):
	global item_data
	global fish_data
	if current_depth > max_depth:
		return

	for entry in os.scandir(directory_path):
		if entry.is_file() and entry.name.endswith(".tres"):
			with open(entry.path, "r", encoding="utf-8", errors="replace") as file:
				item_data = {}
				in_resource_section = False

				for line in file:
					line = line.strip()

					if resource_regex.match(line):
						in_resource_section = True
						continue

					if in_resource_section:
						key_value_match = key_value_regex.match(line)
						if key_value_match:
							key, value = key_value_match.groups()

							if value in {"true", "false"}:
								value = value == "true"
							elif re.match(r"^\d+\.\d+$", value):
								value = float(value)
							elif value.isdigit():
								value = int(value)
							elif value.startswith("[") and value.endswith("]"):
								value = []
							elif value.startswith('"') and value.endswith('"'):
								value = re.sub("﻿", "", value)
								value = re.sub("�", "", value)
								# aaron wanted me to add a liberal joke and i can't be fucked to find smth else to change this to
								value = re.sub("(\(If you have a good idea for this blurb, @MudKipster on the Webfishing Modding Discord!\))", "fucking liberals got to the fish too...", value)
								value = value[1:-1]

							item_data[key] = value

				if "tier" in item_data and "item_name" in item_data:
					name = item_data.pop("item_name")
					item_data["item_name"] = name

					organized_items[name] = item_data

					# If there's a loot_table, organize by loot_table -> fishname
					loot_table = item_data.get("loot_table", "Uncategorized")
					loot_table_items[loot_table][name] = item_data

		elif entry.is_dir():
			await parse_files_in_directory(entry.path, current_depth + 1)

	sorted_items = dict(sorted(organized_items.items()))

	item_data = sorted_items
	fish_data = loot_table_items
