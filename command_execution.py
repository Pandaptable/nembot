import asyncio
import ctypes
import random
from ctypes import wintypes

import win32api

from config import EXEC_FILE, GAME
from globals import COMMAND_QUEUE, csgo_window_handle, nonce_signal, ui_instance
from util.ui import UI

WM_COPYDATA = 0x004A


class TemplateGenerator:
	def __init__(self):
		self.toggle = False

	def generate(self, command):
		self.toggle = not self.toggle
		if self.toggle:
			return f'''	alias unbound1
						alias target "{command}"
						unbound0
						target
						alias unbound0 "alias target"
						'''
		else:
			return f'''	alias unbound0
						alias target "{command}"
						unbound1
						target
						alias unbound1 "alias target"
						'''


gen = TemplateGenerator()


def write_command(command: str) -> None:
	"""
	Write a command to the file that gets executed by the game.

	Args:
		command (str): The command to write.
	"""
	with open(EXEC_FILE, "w", encoding="utf-8") as f:
		command = gen.generate(command)
		f.write(command)


def clear_command() -> None:
	"""
	Clear the command file.
	"""
	with open(EXEC_FILE, "w", encoding="utf-8") as f:
		f.write("")


async def execute_command_csgo(command: str, delay: float | None = None) -> None:
	"""
	Execute a command in CS:GO.

	Args:
		command (str): The command to execute.
		delay (float | None): The time to wait before executing the command in seconds. Defaults to None.
	"""
	if delay is not None and delay != 3621:
		await asyncio.sleep(delay)
		await send_message_async(csgo_window_handle, command)
	if delay == 3621:
		await send_message_async(csgo_window_handle, command)
	else:
		await asyncio.sleep(0.25)
		await send_message_async(csgo_window_handle, command)


def generate_nonce(length: int) -> str:
	"""
	Generate a string of invisible characters of a given length.

	These characters are used to create a unique identifier that is not visible to the user.
	They do not take up any space, so they can be used to uniquely identify a command without
	adding any visible characters.

	Args:
		length (int): The length of the nonce to generate.

	Returns:
		str: The generated nonce.
	"""
	invisible_chars = [
		# "\u200b",  # Zero-width space (this no longer works, it gets turned into a quotation mark by chat?????)
		"\u200c",  # Zero-width non-joiner
		"\u0020",  # Space
		"\u2800",  # Braille blank
	]

	nonce = "".join(random.choice(invisible_chars) for _ in range(length))

	return nonce


async def execute_command_cs2(command: str, delay: float | None = None, check_nonce: bool = True) -> None:
	"""
	Execute a command in CS2.

	Args:
		command (str): The command to execute.
		delay (float | None): The time to wait before executing the command in seconds. Defaults to None.
		check_nonce (bool): Whether to check for nonce when running the command. Defaults to True.

	Notes:

		* This function will retry the command up to 3 times if it fails.
		* It will wait for 2.5 seconds after sending the command to see if it gets executed.
		* If the command fails to get executed after the 3rd retry, it will print a message saying that the command failed to run.
	"""
	nonce = generate_nonce(4) if check_nonce else None
	if check_nonce:
		nonce_signal.register(nonce)

	for _ in range(3):
		if delay is not None and delay != 3621:
			await asyncio.sleep(delay)
		if delay == 3621:
			write_command(command + (f"\necholn {nonce}" if check_nonce else ""))
			await asyncio.sleep(0.05)
			clear_command()
		else:
			await asyncio.sleep(0.25)
			if "say" in command or "say_team" in command:
				write_command(command + (nonce if check_nonce else ""))
				await asyncio.sleep(0.05)
				clear_command()
			else:
				write_command(command)
				await asyncio.sleep(0.05)
				clear_command()

		if check_nonce:
			try:
				await nonce_signal.wait(nonce, timeout=2.5)
			except asyncio.TimeoutError:
				continue
			else:
				break
		else:
			break
	else:
		if check_nonce:
			nonce_signal.unregister(nonce)
			ui_instance.update_status(f"Failed to run command: {command}")
			print(f"Failed to run command {command}")
		return
	ui_instance.update_status("Ready to run command.")


async def execute_command(command: str, delay: float | None = None, check_nonce: bool = True) -> None:
	"""
	Execute a command in the game with optional nonce checking.

	Args:
		command (str): The command to execute.
		delay (float | None): The time to wait before executing the command in seconds. Defaults to None.
		check_nonce (bool): Whether to check for a nonce after executing the command.
	"""
	ui_instance.update_status(f"Executing command: {command}")
	if GAME == "csgo":
		await execute_command_csgo(command, delay, check_nonce)
	else:
		await execute_command_cs2(command, delay, check_nonce)


class COPYDATASTRUCT(ctypes.Structure):
	_fields_ = [
		("dwData", wintypes.LPARAM),
		("cbData", wintypes.DWORD),
		("lpData", wintypes.LPVOID),
	]


async def send_message_async(target_hwnd: str, message: str) -> None:
	"""
	Send a message to the specified window using WM_COPYDATA.

	Args:
		target_hwnd (str): The target window handle.
		message (str): The message to send.
	"""
	loop = asyncio.get_event_loop()
	await loop.run_in_executor(None, send_message, target_hwnd, message)


def send_message(target_hwnd: str, message: str) -> None:
	"""
	Send a message to the specified window using WM_COPYDATA.

	Args:
		target_hwnd (str): The target window handle.
		message (str): The message to send.
	"""
	message_bytes = (message + "\0").encode("utf-8")
	cds = COPYDATASTRUCT()
	cds.dwData = 0
	cds.cbData = len(message_bytes)
	cds.lpData = ctypes.cast(ctypes.create_string_buffer(message_bytes), wintypes.LPVOID)

	win32api.SendMessage(target_hwnd, WM_COPYDATA, 0, ctypes.addressof(cds))
