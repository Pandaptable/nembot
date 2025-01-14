import asyncio

from watchdog.observers import Observer

from command_processing import check_requirements, process_commands
from commands.fetch import find_recently_played
from commands.webfishing import generate_loot_tables, parse_files_in_directory
from config import CONSOLE_FILE, HR_DIRECTORY, HR_FILE, RPC_ENABLED
from console_handler import listen
from database import init_database
from globals import server
from loop.deathchecking import check_death
from loop.discord_rpc import DiscordManager
from loop.heartrate import FileUpdateHandler
from loop.roundtracking import check_round


async def main_loop():
	while True:
		await check_death()
		await process_commands()
		await check_requirements()
		await check_round()
		await asyncio.sleep(0.05)


async def rpc_loop():
	while True:
		await asyncio.sleep(1)
		presence = await DiscordManager.build_presence_from_data(server)
		await DiscordManager.update_presence(presence)


async def shutdown(observer, server):
	observer.stop()
	server.shutdown()

	tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
	[task.cancel() for task in tasks]
	await asyncio.gather(*tasks, return_exceptions=True)
	observer.join()


async def start_server():
	server.start_server()

	if RPC_ENABLED:
		await DiscordManager.initialize()
	else:
		pass

	event_handler = FileUpdateHandler(f"{HR_DIRECTORY + HR_FILE}")
	observer = Observer()
	observer.schedule(event_handler, HR_DIRECTORY, recursive=False)
	observer.start()

	await init_database()
	await find_recently_played()
	await parse_files_in_directory("data/webfishing", 1)
	await generate_loot_tables("fish", "lake")
	await generate_loot_tables("fish", "ocean")
	await generate_loot_tables("fish", "rain")
	await generate_loot_tables("fish", "alien")
	await generate_loot_tables("fish", "void")

	await generate_loot_tables("fish", "water_trash")

	# await generate_loot_tables("none", "seashell")
	# await generate_loot_tables("none", "trash")

	await generate_loot_tables("fish", "metal")

	try:
		log_file = open(CONSOLE_FILE, "r", encoding="utf-8")
		await asyncio.gather(main_loop(), rpc_loop(), listen(log_file))
	except Exception as e:
		print(e)
	finally:
		await shutdown(observer, server)


if __name__ == "__main__":
	try:
		asyncio.run(start_server())
	except KeyboardInterrupt:
		print("Shutting down...")
