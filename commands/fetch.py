import ctypes

import asqlite

from config import DATABASE_NAME
from globals import server, ui_instance

# TODO: run on separate thread for async execution due to ctypes being blocking


class EFriendFlags:
	k_EFriendFlagNone = 0x00
	k_EFriendFlagBlocked = 0x01
	k_EFriendFlagFriendshipRequested = 0x02
	k_EFriendFlagImmediate = 0x04  # direct friends
	k_EFriendFlagClanMember = 0x08
	k_EFriendFlagOnGameServer = 0x10  # recent players
	k_EFriendFlagRequestingFriendship = 0x80
	k_EFriendFlagRequestingInfo = 0x100
	k_EFriendFlagIgnored = 0x200
	k_EFriendFlagIgnoredFriend = 0x400
	k_EFriendFlagChatMember = 0x1000
	k_EFriendFlagAll = 0xFFFF


async def find_recently_played():
	print("\nFetching players...\n")
	ui_instance.update_status("Fetching players...")
	steam_api = ctypes.CDLL("./steam_api64.dll")

	steam_api.SteamAPI_InitSafe.restype = ctypes.c_bool
	steam_api.SteamAPI_InitSafe.argtypes = []
	init = steam_api.SteamAPI_InitSafe()
	if not init:
		print("!SteamAPI_Init")
		return

	steam_api.SteamAPI_SteamFriends_v017.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
	steam_api.SteamAPI_SteamFriends_v017.argtypes = []
	friends_iface = steam_api.SteamAPI_SteamFriends_v017()
	friends_iface_vtable = friends_iface.contents

	GetPersonaName = ctypes.cast(friends_iface_vtable[0], ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p))
	GetFriendCount = ctypes.cast(
		friends_iface_vtable[3],
		ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_int),
	)
	GetFriendByIndex = ctypes.cast(
		friends_iface_vtable[4],
		ctypes.CFUNCTYPE(
			None,
			ctypes.c_void_p,
			ctypes.POINTER(ctypes.c_int64),
			ctypes.c_int,
			ctypes.c_int,
		),
	)

	GetFriendPersonaName = ctypes.cast(
		friends_iface_vtable[7],
		ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_void_p, ctypes.c_longlong),
	)

	# thank you poggu (and more importantly https://github.com/caatge/ for converting this from c++... what the fucking shit is wrong with ctypes :sob:)
	# GetCoplayFriendCount = ctypes.cast(friends_iface_vtable[50], ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p)) # this seems to genuinely be useless...? k_EFriendFlagOnGameServer returns this data..?
	GetCoplayFriend = ctypes.cast(
		friends_iface_vtable[51],
		ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int64), ctypes.c_int),
	)
	GetFriendCoplayTime = ctypes.cast(
		friends_iface_vtable[52],
		ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_void_p, ctypes.c_longlong),
	)
	GetFriendCoplayGame = ctypes.cast(
		friends_iface_vtable[53],
		ctypes.CFUNCTYPE(ctypes.c_uint, ctypes.c_void_p, ctypes.c_longlong),
	)

	# https://partner.steamgames.com/doc/api/ISteamFriends#GetCoplayFriendCount
	# nPlayers = GetCoplayFriendCount(friends_iface)
	flags = EFriendFlags.k_EFriendFlagImmediate | EFriendFlags.k_EFriendFlagOnGameServer
	nPlayers = GetFriendCount(friends_iface, flags)

	players = []

	for i in range(nPlayers):
		steamid = ctypes.c_int64(0)
		GetCoplayFriend(friends_iface, ctypes.byref(steamid), i)  # Ensure steamid is passed by reference
		GetFriendByIndex(friends_iface, ctypes.byref(steamid), i, flags)
		timestamp = GetFriendCoplayTime(friends_iface, steamid)
		app = GetFriendCoplayGame(friends_iface, steamid)
		name = GetFriendPersonaName(friends_iface, steamid)
		name = name.decode("utf-8")
		players.append({
			"name": name,
			"id": steamid.value,
			"time": timestamp,
			"app": app,
		})
		# print(f"Player {i} - Name: {name} - ID: {steamid.value} - Time: {timestamp} - App: {app}")

	self_id = server.get_info("provider", "steamid")
	self_name = GetPersonaName(friends_iface, self_id)
	self_name = self_name.decode("utf-8")
	self_time = server.get_info("provider", "timestamp")
	self_app = server.get_info("provider", "appid")

	players.append({
		"name": self_name,
		"id": self_id,
		"time": self_time,
		"app": self_app,
	})
	# print(f"Self - Name: {self_name} - ID: {self_id} - Time: {self_time} - App: {self_app}")

	players.sort(key=lambda p: p["time"])

	for i, player in enumerate(players):
		# print(f"Player {i} - Name: {player['name']} - ID: {player['id']} - Time: {player['time']} - App: {player['app']}")
		await insert_player(player["id"], player["name"].replace(";", ":"))

	ui_instance.update_status("Players fetched.")


async def insert_player(steamid: int, username: str):
	async with asqlite.connect(DATABASE_NAME) as connection:
		async with connection.cursor() as cursor:
			await cursor.execute(
				"""
				INSERT INTO players (steamid, username)
				VALUES (?, ?)
				ON CONFLICT(steamid) DO UPDATE SET
					username = excluded.username
				""",
				(steamid, username),
			)
			await connection.commit()
