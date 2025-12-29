import asyncio
import random
import re

import aiohttp
from lingua import Language

from command_execution import execute_command
from commands.container import open_container
from commands.fact import get_fact
from commands.fetch import find_recently_played
from commands.webfishing import cast_line
from config import *
from database import check_if_player_exists, get_balance, insert_command
from globals import BANNED_LIST, COMMAND_LIST, COMMAND_QUEUE, COMMAND_REGEX, LANGUAGE_SHORT_CODES, TEAMS, TRANSLATION_QUEUE, detector, server
from util.translate import translate_message


async def parse(line: str):
	"""
	Parses a line of text to extract command details and processes it if valid.

	Args:
		line (str): The input text line containing command information.

	Extracts information such as team, username, location, command, and its arguments
	using a regex pattern. If a valid command is found, the user's steam ID is checked
	or retrieved, and the command is logged into the database. The command is then added
	to a processing queue.
	"""
	regex = re.search(COMMAND_REGEX, line, flags=re.UNICODE | re.VERBOSE)
	if regex:
		team = regex.group("team")
		username = regex.group("username").replace(";", ":")
		location = regex.group("location")
		dead = regex.group("dead_status")
		command = regex.group("command").replace(";", ":")
		args = regex.group("args").replace(";", ":")
	else:
		team = ""
		username = ""
		location = ""
		dead = ""
		command = ""
		args = ""

	# null checking for commands
	if not command:
		return

	if args:
		full_message = command + " " + args
	else:
		full_message = command

	if command.lower() in COMMAND_LIST:
		steamid = await check_if_player_exists(username)
		if not steamid:
			await find_recently_played()
			steamid = await check_if_player_exists(username)

		if steamid:
			steamid = int(steamid)
			COMMAND_QUEUE.append((steamid, command, args, username, team, dead, location))

	if LANGUAGE_DETECTION:
		steamid = await check_if_player_exists(username)
		if steamid == int(server.get_info("provider", "steamid")):
			pass
		else:
			# detector = LanguageDetectorBuilder.from_all_languages().with_preloaded_language_models().build()
			translated_command = detector.detect_language_of(full_message)
			if translated_command != Language.ENGLISH:
				translated_message, detected_language = await translate_message(full_message)
				if detected_language not in LANGUAGE_SHORT_CODES:
					return
				if translated_message is not None and translated_message != full_message:
					TRANSLATION_QUEUE.append((translated_message, username, detected_language, team))


async def check_requirements() -> bool:
	"""
	Check if the bot should process commands based on the current phase.

	Returns:
		bool: True if the bot should process commands, False otherwise.
	"""
	global should_process_commands

	if server.get_info("map", "phase") == "live" or "warmup":
		should_process_commands = True
		return True

	should_process_commands = False
	return False


async def process_commands():
	"""
	Process commands in the queue if the bot should process commands.
	"""
	if await check_requirements():
		if COMMAND_QUEUE:
			steamid, cmd, args, user, team, dead, location = COMMAND_QUEUE.popleft()
			# await asyncio.sleep(0.25)
			await switchcase_commands(steamid, cmd, args, user, team, dead, location)
			timestamp = server.get_info("provider", "timestamp")
			command_data = cmd.replace("!", "")
			command_data = command_data + " " + args
			await insert_command(steamid, user, command_data, team, dead, location, timestamp)
		if TRANSLATION_QUEUE:
			message, username, language, translation_team = TRANSLATION_QUEUE.popleft()
			await process_translations(message, username, language, translation_team)


async def switchcase_commands(steamid: int, cmd: str, args: str, user: str, team: str, dead: str, location: str) -> None:
	"""
	Process commands in the queue if the bot should process commands.

	Args:
		steamid (int): The SteamID of the player that sent the command.
		cmd (str): The command issued by the player.
		args (str): The arguments provided with the command.
		user (str): The username of the player that sent the command.
		team (str): The team of the player that sent the command.
		dead (str): The dead status of the player that sent the command.
		location (str): The location of the player that sent the command.
	"""
	cmd = cmd.lower()
	if steamid not in BANNED_LIST:
		match cmd:
			# case "!disconnect" | "!dc":
			#     await execute_command("disconnect", 0.5)
			# case "!quit" | "!q":
			#     await execute_command("quit", 0.5)
			case _ if cmd == f"{COMMAND_PREFIX}i" or cmd == f"{COMMAND_PREFIX}inspect":
				if team in TEAMS:
					if args:
						inspect_link = re.search(
							r"steam:\/\/rungame\/730\/[0-9]+\/\+csgo_econ_action_preview%20([A-Za-z0-9]+)",
							args,
						)
						if inspect_link:
							await execute_command(f"gameui_activate;csgo_econ_action_preview {inspect_link.group(1)}\n say {PREFIX} Opened inspect link on my client.", 3621, False)
						else:
							await execute_command(f"say {PREFIX} Invalid inspect link.")
					else:
						await execute_command(f"say {PREFIX} No inspect link provided.")
			case _ if cmd == f"{COMMAND_PREFIX}switchhands":
				if team in TEAMS:
					await execute_command("switchhands", 3621, False)
			case _ if cmd == f"{COMMAND_PREFIX}flash":
				if team in TEAMS:
					await execute_command(f"say_team {PREFIX} fuck you.")
					for _ in range(13):
						await execute_command("flashbangs", 3621, False)
						await asyncio.sleep(0.01 / 13)
			case _ if cmd == f"{COMMAND_PREFIX}fish" or cmd == f"{COMMAND_PREFIX}〈͜͡˒":  # regex would need to be changed to properly match the fish kaomoji: !〈͜͡˒ ⋊
				if team in TEAMS or not dead:
					await cast_line(steamid, user, team)
				else:
					await execute_command(f"say {PREFIX} You cannot fish while dead.")
			case _ if cmd == f"{COMMAND_PREFIX}info":
				if team in TEAMS:
					await execute_command(f"say_team {PREFIX} github.com/Pandaptable/nembot, reads console.log and parses chat through it (aka not a cheat)")
				else:
					await execute_command(f"say {PREFIX} github.com/Pandaptable/nembot, reads console.log and parses chat through it (aka not a cheat)")
			case _ if cmd == f"{COMMAND_PREFIX}location":
				if team in TEAMS:
					message = "you're dead dumbass." if dead else f"Your current location: {location}"
					await execute_command(f"say_team {PREFIX} {message}")
			case _ if cmd == f"{COMMAND_PREFIX}fact":
				if team in TEAMS:
					fact = await get_fact()
					await execute_command(f"say_team {PREFIX} {fact}")
				else:
					fact = await get_fact()
					await execute_command(f"say {PREFIX} {fact}")
			case _ if cmd == f"{COMMAND_PREFIX}drop":
				if team in TEAMS:
					await execute_command("drop", 3621, False)  # funny 3621 placeholder for shit code to execute with 0 delay
			case _ if cmd == f"{COMMAND_PREFIX}help" or cmd == f"{COMMAND_PREFIX}commands" or cmd == f"{COMMAND_PREFIX}cmds":
				if team in TEAMS:
					await execute_command(
						f"say_team {PREFIX} {COMMAND_PREFIX}help (shows this message) | {COMMAND_PREFIX}bal | {COMMAND_PREFIX}fish | {COMMAND_PREFIX}fact | {COMMAND_PREFIX}i <inspect link> | {COMMAND_PREFIX}info (info on the bot) | {COMMAND_PREFIX}location | {COMMAND_PREFIX}drop | {COMMAND_PREFIX}switchhands | {COMMAND_PREFIX}case | {COMMAND_PREFIX}capsule"
					)
				else:
					await execute_command(
						f"say {PREFIX} {COMMAND_PREFIX}help (shows this message) | {COMMAND_PREFIX}bal | {COMMAND_PREFIX}fish | {COMMAND_PREFIX}fact | {COMMAND_PREFIX}info (info on the bot) | {COMMAND_PREFIX}case | {COMMAND_PREFIX}capsule"
					)
			case _ if cmd == f"{COMMAND_PREFIX}balance" or cmd == f"{COMMAND_PREFIX}bal" or cmd == f"{COMMAND_PREFIX}money":
				if team in TEAMS:
					await execute_command(f"say_team {PREFIX} You have ₶{await get_balance(steamid)} hegemony")
				else:
					await execute_command(f"say {PREFIX} You have ₶{await get_balance(steamid)} hegemony")
			case _ if cmd == f"{COMMAND_PREFIX}steamid":
				if team in TEAMS:
					await execute_command(f"say_team {PREFIX} Your SteamID is: {steamid}")
				else:
					await execute_command(f"say {PREFIX} Your SteamID is: {steamid}")
			case _ if cmd == f"{COMMAND_PREFIX}heartrate" or cmd == f"{COMMAND_PREFIX}hr":
				if HR_ENABLED:
					if team in TEAMS:
						await execute_command(f"say_team {PREFIX} My heart rate is: {await get_heart_rate()} bpm")
					else:
						await execute_command(f"say {PREFIX} My heart rate is: {await get_heart_rate()} bpm")
			case _ if cmd == f"{COMMAND_PREFIX}case":
				if team in TEAMS or not dead:
					container_type = "case"
					await open_container(args, user, steamid, team, cmd, container_type)
				else:
					await execute_command(f"say {PREFIX} You cannot open a container while dead.")
			case _ if cmd == f"{COMMAND_PREFIX}capsule":
				if team in TEAMS or not dead:
					container_type = "capsule"
					await open_container(args, user, steamid, team, cmd, container_type)
				else:
					await execute_command(f"say {PREFIX} You cannot open a container while dead.")
			case _ if cmd == f"{COMMAND_PREFIX}shock":
				if OPENSHOCK_ENABLED:
					if team in TEAMS:
						await shock(args, user, steamid)
	# else:
	# 	if team in TEAMS:
	# 		await execute_command(f"say_team {PREFIX} You are banned from using the bot. fuck you.")
	# 	else:
	# 		await execute_command(f"say {PREFIX} You are banned from using the bot. fuck you.")


# TODO: add options for console, team chat, and maybe windows notification or smth (or just bot console lmfao)
async def process_translations(message: str, username: str, language: str, team: str):
	"""
	Process translations for the given message and username.

	Args:
		message (str): The message to process.
		username (str): The username of the user who sent the message.
		language (str): The suspected language of the message.
		team (str): The team of the user who sent the message.
	"""
	if team in TEAMS:
		await execute_command(f"say_team {PREFIX} {username} says ({language}): {message}")
	else:
		await execute_command(f"say {PREFIX} {username} says ({language}): {message}")


async def shock(args: str, username: str, steamid: int):
	"""
	Send a shock to the user.

	Args:
		args (str): The args to parse for the intensity and duration of the shock.
		username (str): The username of the user who sent the command.
		steamid (int): The SteamID of the user who sent the command.
	"""
	args_list = args.split(" ")
	try:
		intensity = int(args_list[0])
		duration = float(args_list[1])
	except (ValueError, IndexError):
		await execute_command(
			f"say_team {PREFIX} Invalid intensity or duration. Usage: !shock <intensity (0-{OPENSHOCK_STRENGTH_RANGE[1]})> <duration (0.3-{OPENSHOCK_DURATION_RANGE[1] / 1000} seconds)>"
		)
		return

	if OPENSHOCK_PUNISHMENT_TYPE == "random":
		shocker_list = [random.choice(OPENSHOCK_SHOCKER_LIST)]
	elif OPENSHOCK_PUNISHMENT_TYPE == "one":
		shocker_list = [OPENSHOCK_SHOCKER_LIST[0]]
	else:
		shocker_list = OPENSHOCK_SHOCKER_LIST

	if not args or not isinstance(duration, float) or not isinstance(intensity, int):
		await execute_command(
			f"say_team {PREFIX} No intensity or duration provided. Usage: !shock <intensity (0-{OPENSHOCK_STRENGTH_RANGE[1]})> <duration (0.3-{OPENSHOCK_DURATION_RANGE[1] / 1000} seconds)>"
		)
	else:
		if len(args_list) != 2:
			await execute_command(
				f"say_team {PREFIX} Invalid intensity or duration. Usage: !shock <intensity (0-{OPENSHOCK_STRENGTH_RANGE[1]})> <duration (0.3-{OPENSHOCK_DURATION_RANGE[1] / 1000} seconds)>"
			)
		else:
			if int(intensity) not in range(0, OPENSHOCK_STRENGTH_RANGE[1] + 1) or float(duration) not in [round(x / 1000, 3) for x in range(300, OPENSHOCK_DURATION_RANGE[1] + 1)]:
				await execute_command(
					f"say_team {PREFIX} Invalid intensity or duration. Usage: !shock <intensity (0-{OPENSHOCK_STRENGTH_RANGE[1]})> <duration (0.3-{OPENSHOCK_DURATION_RANGE[1] / 1000} seconds)>"
				)
				return
		intensity = int(intensity)
		duration = int(float(duration) * 1000)

		shocks = [{"id": shock_id, "type": OPENSHOCK_TYPE, "intensity": intensity, "duration": duration} for shock_id in shocker_list]

		payload = {"shocks": shocks, "customName": f"Shocked by [{username} ({steamid})](https://steamcommunity.com/profiles/{steamid})"}

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
					elif response.status == 500:
						pass
					else:
						print(f"Failed to activate shocker. Response: {response}")
			except aiohttp.ClientError as e:
				print(f"An error occurred: {e}")


async def get_heart_rate():
	"""
	Get your heartrate.

	Returns:
		int: The heart rate of the user.
	"""
	return open(f"{HR_DIRECTORY + HR_FILE}", "r", encoding="utf-8").read().splitlines()[0]
