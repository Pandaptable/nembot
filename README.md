this repo is basically EOL lmao, feel free to still use it or whatever, i'll still update it from time to time but will offer 0 support, valve has killed any easy way for me to send console commands externally.. so i have to resort to sending keypresses to a file

~~eventually i will likely rewrite this and implement telnet, but that only works on linux because valve is fucking retarded.. so until i switch to linux this repo is 99% EOL.~~
i forgot valve patched this too.

~~(anything < python 3.12 breaks i do not know why... it's the GSI library tho :3)~~

~~no this doesn't read memory it's not a cheat, i'm just using fucking [schizo methods](https://github.com/Pandaptable/CS-dotfiles/tree/main/selfbot/ticks) of sending console commands (exec_async with `n` getting executed every 50 frames that is aliased to `exec selfbot`)~~

~~## Setup~~
~~1. `uv sync`~~
~~2. `cp config_default.py config.py`~~
~~3. edit config~~
~~4. setup CS CFG folder and launch options~~
	~~- add the selfbot folder from [this](https://github.com/Pandaptable/CS-dotfiles) repo into your cfg folder~~
	~~- add `alias n "exec selfbot.cfg"` into your autoexec (or whatever you named the file at the root of your cfg directory)~~
	~~- add `exec "selfbot/setup.cfg"` into your autoexec (in main menu, it needs `sv_cheats 1` so it will break otherwise)~~
	~~- add `gamestate_integration_GSI.cfg` to the root of your cfg folder and use the same auth token you set in config~~
 	~~- add `-condebug` and `-conclearlog` to your launch options. (i'd also recommend adding `-allow_third_party_software` as i may implement something with window handles, which could possibly cause issues?)~~
 	~~- highly recommend adding`log_flags InputService +donotecho` to the end of your autoexec :3~~
~~5. download the [steamworks SDK](https://partner.steamgames.com/downloads/list) dll for version 1.61~~
~~7. install the game Fish (steam://install/3073680) to properly get the SteamAPI to initialize (nembot uses steamworks), you dont have to run it~~
~~8. `uv run main.py`~~
~~9. :trollface:~~

~~### credits for fish (other than webfishing)~~
~~[More Fishing](https://github.com/reallymako/MoreFishingWEBFISHING)~~

~~[Fishing Expanded](https://github.com/coolbot100s/FishingExpanded)~~

~~[InsaniquariumWEB](https://github.com/MonkeyMan1242/InsaniquariumWEB)~~

~~[Webfishing101](https://github.com/Mudkipster/Webfishing101)~~

~~[WebValley](https://thunderstore.io/c/webfishing/p/Junohno/WebValley/)~~

~~[SuperMarioWeb](https://github.com/MonkeyMan1242/SuperMarioWEB)~~

~~[Webnautica](https://github.com/SecondEgg101/Webnautica)~~

~~[PortalFish](https://thunderstore.io/c/webfishing/p/Amma/PortalFish/)~~

~~[CatchThemAll](https://thunderstore.io/c/webfishing/p/hostileonion/CatchThemAll/)~~


~~### more credits~~
~~[RTSS Shared Memory](https://github.com/upgradeQ/RTSSSharedMemoryPythonNET) in python (dll being redistributed along with the example script they have, need to provide source due to license)~~
