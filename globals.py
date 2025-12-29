from collections import deque

import win32gui
from lingua import Language, LanguageDetectorBuilder
from PyQt6.QtWidgets import QApplication

from config import COMMAND_PREFIX, GAME, GSI_TOKEN
from gsi.server import GSIServer
from util.signal import EventSignal
from util.ui import UI

BANNED_LIST = [
	76561198055654571,
	76561198162871889,
	76561198398160009,
	76561198189637015,
	76561198078389589,
	76561198133974124,
]


COMMAND_LIST = [
	f"{COMMAND_PREFIX}i",
	f"{COMMAND_PREFIX}inspect",
	f"{COMMAND_PREFIX}switchhands",
	f"{COMMAND_PREFIX}flash",
	f"{COMMAND_PREFIX}fish",
	f"{COMMAND_PREFIX}〈͜͡˒",
	f"{COMMAND_PREFIX}info",
	f"{COMMAND_PREFIX}location",
	f"{COMMAND_PREFIX}fact",
	f"{COMMAND_PREFIX}drop",
	f"{COMMAND_PREFIX}help",
	f"{COMMAND_PREFIX}commands",
	f"{COMMAND_PREFIX}cmds",
	f"{COMMAND_PREFIX}balance",
	f"{COMMAND_PREFIX}bal",
	f"{COMMAND_PREFIX}money",
	f"{COMMAND_PREFIX}steamid",
	f"{COMMAND_PREFIX}heartrate",
	f"{COMMAND_PREFIX}hr",
	f"{COMMAND_PREFIX}shock",
	f"{COMMAND_PREFIX}case",
	f"{COMMAND_PREFIX}capsule",
]


# List of strings to filter out of console output (if the line contains anything in this then it'll be filtered)
PRE_FILTER = [
	"[InputSystem]",
	"[InputService]",
	"[NetSteamConn]",
	"[Networking]",
	"[Host]",
	"[VProf]",
	"[Client]",
	"[EngineServiceManager]",
	"[CL CommandQueue]",
	"[SplitScreen]",
	"[RenderSystem]",
	"[Panorama]",
	"[SteamNetSockets]",
	"[RenderPipelineCsgo]",
	"[VScript]",
	"[stringtables]",
	"[SignonState]",
	"[WorldRenderer]",
	"[AnimResource]",
	"[ResourceSystem]",
	"[SoundSystem]",
	"[Shooting]",
	"[HostStateManager]",
	"[Server]",
	"[BuildSparseShadowTree]",
	"[SteamAudio]",
	"[SV CommandQueue]",
	"[Prediction]",
	"[SceneFileCache]",
	"[SceneSystem]",
	"execing selfbot",
	"execing movement/de-subticks/",
	"Invalid content height",
	"Certificate expires in",
	"**** Panel",
	"Interpreting bind command as:",
	"CCSGO_BlurTarget",
	"Entry player was not found",
	"CPlayerVoiceListener",
	"GameTypes: missing",
	"Unable to read",
	"failed to load file",
	"CNavGenParams",
	"failed to find",
	"Telling Steam not to update",
	"Telling Steam it is safe",
	"**** Unable",
	"ms Client",
	"ms FileSystem",
	"ms Prediction",
	"ms Frame",
	"ms SDL",
	"PlayerStatsUpdate",
	"used during construction differ",
	"Invalid image URL",
	"ReadSteamRemoteStorageFile",
	"CAnimGraphNetworkedVariables::",
	"CAsyncWriteInProgress::",
	"WriteSteamRemoteStorageFileAsync",
	"ChangeGameUIState",
	"This is usually a symptom of a general performance problem such as thread starvation.",
	"Obtained direct RTT measurements to relays in",
	"CS_App_Lifetime_Gamestats:",
	"Inventory filter setting",
	"Ping measurement completed after",
	"via direct route",
	"(This list may include POPs without any gameservers)",
	"Measured RTT to",
	"SDR ping location:",
	"Forcing SDR connection to",
	"Received SDR ticket for [",
	"Confirmation number",
	"Excessive frame time of ",
	"Present_RenderDevice",
	" not found in map ",
	"Unknown command: sellback",
	"CreateProceduralSfx:",
	"Ping measurement has been active for ",
	"    bind scancode",
	"Executing server command (",
	"ResetBreakpadAppId: ",
	"Logging into anonymous listen server account.",
	"Setting mapgroup to ",
	"Invalid counterterrorist spawnpoint",
	"Invalid terrorist spawnpoint",
	"Achievements disabled: cheats turned on in this app session.",
	"6ms Server ",
	"missing sounds dir. Fixing for now.",
	"[SoundSystemLowLevel]",
	"models/hostage/v_hostage_arm.vmdl :: draw",
	"--------  -------  --------  --------------",
	"excl ms   excl %   incl ms   group",
	"ms, tolerance:   ",
	"Framerate spike report",
	"ms    ",
	"Bad resource name <NULL_MODEL>",
	"Can't set position/velocity on whiz sound",
	"CMatchSessionOnlineClient::UpdateSessionSettings is",
	"SteamNetworkingSockets lock",
	"OnPreResetRound",
	"ChangeTeam() CTMDBG",
	"GC Connection established for server version",
	"EVERYONE CAN BUY!",
	"ms  EventFrameBoundary_t",
	"ms  Client Rendering",
]

REGION_FILTER = [
	"ord:",
	"atl:",
	"iad:",
	"dfw:",
	"dfw2:",
	"sea:",
	"lax:",
	"lhr:",
	"par:",
	"ams4:",
	"ams:",
	"sto:",
	"sto2:",
	"fra:",
	"waw:",
	"eat:",
	"hel:",
	"mad:",
	"vie:",
	"tyo:",
	"eze:",
	"seo:",
	"hkg4:",
	"can:",
	"cant:",
	"pwg:",
	"canm:",
	"tgdm:",
	"shb:",
	"pvgt:",
	"canu:",
	"pwj:",
	"pwz:",
	"pww:",
	"maa2:",
	"pwu:",
	"bom2:",
	"lim:",
	"dfwm:",
	"  gru: ",
	"  scl: ",
	"(front=",
	"ms faster than direct ping of ",
	"-- below this line ping exceeds mm_dedicated_search_maxping --",
]

PRINT_FILTER = PRE_FILTER + REGION_FILTER


# https://regex101.com/r/pTapEF/7
csgo_regex = (
	r"(?:\d{2}\/){2}\d{4}\s-\s\d{2}:(?:\d{2}:){2}\s(?P<dead_status>\*DEAD\*)?\s?(?:\((?P<team>[^)]+)\))?\s?(?P<username>.*?)‎\s(?:@\s(?P<location>.*?))?\s?:(?:\s)*(?P<command>\S+)?\s(?P<args>.*)?"
)

# https://regex101.com/r/1lYpb1/8
cs2_regex = r"\[(?P<team>ALL|CT|T)\]\s+(?P<username>.*)‎(?:﹫(?P<location>.*?))?\s*(?P<dead_status>\[DEAD\])?:(?:\s)*(?P<command>\S+)?\s(?P<args>.*)?"


if GAME == "csgo":
	COMMAND_REGEX = csgo_regex
else:
	COMMAND_REGEX = cs2_regex

CLIENT_ID = 872181511334543370

# TODO: change gsi library or add type definitions to everything
server = GSIServer(("127.0.0.1", 3000), GSI_TOKEN)

LANGUAGES = [
	Language.ENGLISH,
	Language.FRENCH,
	Language.GERMAN,
	Language.SPANISH,
	Language.TURKISH,
	Language.RUSSIAN,
	Language.UKRAINIAN,
	Language.CHINESE,
	Language.JAPANESE,
	Language.KOREAN,
	Language.POLISH,
]

LANGUAGE_SHORT_CODES = [
	"en",
	"fr",
	"de",
	"es",
	"tr",
	"ru",
	"uk",
	"zh",
	"ja",
	"ko",
	"pl",
]

detector = LanguageDetectorBuilder.from_languages(*LANGUAGES).build()

csgo_window_handle = win32gui.FindWindow("Valve001", None)

TEAMS = ["CT", "T", "Terrorist", "Counter-Terrorist"]

last_round = None
last_phase = None
nonce_signal = EventSignal()

app = QApplication([])
ui_instance = UI()
ui_instance.start()


COMMAND_QUEUE = deque()
TRANSLATION_QUEUE = deque()
