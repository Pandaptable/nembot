import asyncio
import ctypes
from ctypes import wintypes

import win32api
import win32gui

from config import *
from globals import csgo_window_handle

WM_COPYDATA = 0x004A

async def write_command(command):
	with open(EXEC_FILE, "w", encoding='utf-8') as f:
		f.write(command)

async def clear_command():
	with open(EXEC_FILE, "w", encoding='utf-8') as f:
		f.write("")

async def execute_command_csgo(command, delay=None):
	if delay is not None and delay != 3621:
		await asyncio.sleep(delay)
		send_message(csgo_window_handle, command)
	if delay == 3621:
		send_message(csgo_window_handle, command)
	else:
		await asyncio.sleep(0.4)
		send_message(csgo_window_handle, command)


async def execute_command_cs2(command, delay=None):
	if delay is not None:
		await asyncio.sleep(delay)
	await asyncio.sleep(0.25) # wait 0.25 seconds for chat delay, 0.15 should work but is very inconsistent... fuck valve
	await write_command(command)
	await asyncio.sleep(0.015625) # wait 1 tick (may need to adjust, more testing needed)
	await clear_command()


async def execute_command(command, delay=None):
	if GAME == "csgo":
		await execute_command_csgo(command, delay)
	else:
		await execute_command_cs2(command, delay)


class COPYDATASTRUCT(ctypes.Structure):
	_fields_ = [
		("dwData", wintypes.LPARAM),
		("cbData", wintypes.DWORD),
		("lpData", wintypes.LPVOID),
	]


# TODO: make this async
def send_message(target_hwnd, message):
	message_bytes = (message + "\0").encode("utf-8")
	cds = COPYDATASTRUCT()
	cds.dwData = 0
	cds.cbData = len(message_bytes)
	cds.lpData = ctypes.cast(
		ctypes.create_string_buffer(message_bytes), wintypes.LPVOID
	)

	win32api.SendMessage(target_hwnd, WM_COPYDATA, 0, ctypes.addressof(cds))