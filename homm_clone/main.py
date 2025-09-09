import pygame
import time # For simple non-blocking delay
from gui.lobby import LobbyScreen
from network.client import GameClient # Import GameClient
from network.host import GameHost # Import GameHost
from game_logic.hex_grid import HexGrid # STEP 1a
from gui.game_screen import GameScreen   # STEP 1a

# Initialize Pygame
pygame.init()

# Set screen dimensions
screen_width = 1000 
screen_height = 700 
screen = pygame.display.set_mode((screen_width, screen_height))

# Set window title
pygame.display.set_caption("HoMM Clone") # General title

# --- Game State ---
current_screen = "lobby"
game_screen_ui = None # STEP 1b
game_grid = None      # STEP 1b

# --- Network Client & Host ---
player_name_input = input("Enter your player name (default: PyPlayer): ") or f"PyPlayer{int(time.time())%100}"
game_client = GameClient(player_name=player_name_input) 
game_host = None 

# --- Lobby Screen Instance ---
lobby_screen = LobbyScreen(screen) # This needs to be available for lobby state

# --- Initial Game Discovery (if not starting directly into game screen for testing) ---
if current_screen == "lobby":
    lobby_screen.connection_status_message = "Searching for games..."
    lobby_screen.discovered_games = game_client.discover_games(timeout=2.0) 
    if not lobby_screen.discovered_games:
        lobby_screen.connection_status_message = "No games found. Click Refresh."
    else:
        lobby_screen.connection_status_message = f"Found {len(lobby_screen.discovered_games)} game(s). Select one to connect."


# --- Main Game Loop ---
running = True
was_connected = False 

while running:
    # --- Event Handling ---
    action = None # Reset action each loop iteration
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        # Pass event to current screen's handler
        if current_screen == "lobby":
            action = lobby_screen.handle_event(event, game_client)
        elif current_screen == "game_map":
            if game_screen_ui:
                action = game_screen_ui.handle_event(event)
        
        # --- Handle Global Actions or Actions that Change Screen ---
        if action == "quit_game": # Example action from GameScreen to quit
            print("MAIN: Quit_game action received. Shutting down.")
            running = False
            break # Exit event loop early if quitting

    # --- Process Actions returned by screen handlers (mostly for lobby) ---
    if current_screen == "lobby" and action: # Ensure action is processed only if still in lobby
        if action == "refresh_games":
            lobby_screen.connection_status_message = "Refreshing games..."
            lobby_screen.current_player_list = [] 
            lobby_screen.selected_game_index = None
            pygame.display.flip() 
            lobby_screen.discovered_games = game_client.discover_games(timeout=2.0)
            if not lobby_screen.discovered_games:
                lobby_screen.connection_status_message = "No games found after refresh."
            else:
                lobby_screen.connection_status_message = f"Found {len(lobby_screen.discovered_games)} game(s)."
        
        elif action == "host_game":
            if game_host:
                lobby_screen.connection_status_message = "Already hosting! Stop current game first."
            elif game_client.is_connected:
                lobby_screen.connection_status_message = "Already connected to a game. Disconnect first."
            else:
                lobby_screen.connection_status_message = "Starting host..."
                pygame.display.flip()
                game_host = GameHost(host_name=f"{game_client.player_name}'s Game", tcp_port=5555) 
                game_host.start()
                time.sleep(0.5) 
                lobby_screen.connection_status_message = "Connecting to local game..."
                pygame.display.flip()
                connection_successful = game_client.connect("127.0.0.1", game_host.tcp_port, player_name_override=game_client.player_name)
                if connection_successful:
                    lobby_screen.connection_status_message = f"Now hosting on port {game_host.tcp_port}. You are in the lobby."
                    lobby_screen.is_hosting = True 
                    lobby_screen.discovered_games = [] 
                    lobby_screen.selected_game_index = None 
                else:
                    lobby_screen.connection_status_message = "Failed to connect client to local host."
                    if game_host: game_host.stop(); game_host = None
                    lobby_screen.is_hosting = False 
        
        elif action == "initiate_game_start": # STEP 1c
            if game_host is not None: 
                print("MAIN: Host is initiating game start...") 
                map_cols_to_send = 20 # Example dimensions
                map_rows_to_send = 15 # Example dimensions
                game_host.broadcast_game_started(map_cols_to_send, map_rows_to_send)
                lobby_screen.connection_status_message = "Starting game for all players..."
            else:
                print("MAIN: Non-host tried to initiate_game_start. Ignoring.")
        
        elif action == "toggle_ready_state":
            if game_client.is_connected:
                current_local_ready_state = lobby_screen.local_player_is_ready 
                game_client.send_ready_state(current_local_ready_state)
            else:
                lobby_screen.local_player_is_ready = False 
                lobby_screen.connection_status_message = "Cannot set ready state: Not connected."
                print("Error: Tried to toggle ready state but not connected.")

        elif isinstance(action, tuple) and action[0] == "connect_to_game":
            if game_client.is_connected: 
                lobby_screen.connection_status_message = "Already connected. Disconnect first?"
            elif game_host:
                 lobby_screen.connection_status_message = "Currently hosting. Stop hosting to join another game."
            else:
                _, host_ip, tcp_port = action
                lobby_screen.connection_status_message = f"Connecting to {host_ip}:{tcp_port}..."
                lobby_screen.current_player_list = [] 
                pygame.display.flip() 
                connection_successful = game_client.connect(host_ip, tcp_port, player_name_override=game_client.player_name)
                if not connection_successful:
                    lobby_screen.connection_status_message = f"Failed to connect to {host_ip}:{tcp_port}."
                    if game_client.is_connected or game_client.tcp_socket:
                         game_client.disconnect()

    # --- Check for Game Start from Network (applies to all clients, including host's client) --- STEP 1d
    if game_client and game_client.is_connected and game_client.game_has_started and current_screen == "lobby":
        print(f"MAIN: Game start signal received. Transitioning to game map. Map: {game_client.game_map_cols}x{game_client.game_map_rows}") 
        if game_client.game_map_cols and game_client.game_map_rows:
            game_grid = HexGrid(cols=game_client.game_map_cols, rows=game_client.game_map_rows)
            game_screen_ui = GameScreen(screen, game_grid) # Assuming default hex_size for now
            current_screen = "game_map"
            pygame.display.set_caption(f"HoMM Clone - Game In Progress ({game_client.player_name})")

            # Reset game_has_started flag on client to prevent re-triggering transition
            # game_client.game_has_started = False # Deferred as per original instructions to handle "back to lobby" later
        else:
            print("MAIN: Game started signal received, but map dimensions are missing. Cannot transition.")
            game_client.game_has_started = False # Reset to avoid loop


    # --- Update GUI from GameClient State (Lobby specific) ---
    if current_screen == "lobby": # This block should only run if we are still in the lobby
        is_connected_now = game_client.is_connected 
        if is_connected_now:
            with game_client.lock: 
                 lobby_screen.current_player_list = list(game_client.player_list) 
            if game_client.player_id is not None: 
                for player_data in lobby_screen.current_player_list:
                    if player_data.get("id") == game_client.player_id:
                        authoritative_local_ready_state = player_data.get("is_ready", False)
                        if lobby_screen.local_player_is_ready != authoritative_local_ready_state:
                            lobby_screen.local_player_is_ready = authoritative_local_ready_state
                        break 
            if not was_connected: 
                selected_game_name = "the game"
                if lobby_screen.selected_game_index is not None and \
                   lobby_screen.selected_game_index < len(lobby_screen.discovered_games): # Check if discovered_games is populated
                     selected_game_details = lobby_screen.discovered_games[lobby_screen.selected_game_index]
                     selected_game_name = selected_game_details.get('game_name', 'the game')
                lobby_screen.connection_status_message = f"Successfully connected to {selected_game_name} as {game_client.player_name} (ID: {game_client.player_id})!"
        else: 
            lobby_screen.current_player_list = [] 
            if was_connected: 
                status_msg_prefix = "Disconnected."
                if game_host: 
                    print("Client disconnected while hosting. Stopping host.")
                    game_host.stop(); game_host = None
                    lobby_screen.is_hosting = False
                    status_msg_prefix = "Host stopped."
                if "Connecting to" not in lobby_screen.connection_status_message and \
                   "Refreshing" not in lobby_screen.connection_status_message and \
                   "Failed to connect" not in lobby_screen.connection_status_message:
                    lobby_screen.connection_status_message = f"{status_msg_prefix} Select a game or host."
        was_connected = is_connected_now


    # --- Drawing --- STEP 1e
    screen.fill(lobby_screen.colors.get("white", (255,255,255))) # Default background

    if current_screen == "lobby":
        lobby_screen.draw(screen)
    elif current_screen == "game_map":
        if game_screen_ui:
            game_screen_ui.draw(screen)
        else: 
            loading_font = pygame.font.Font(None, 50)
            text_surf = loading_font.render("Loading Game Map...", True, (0,0,0))
            text_rect = text_surf.get_rect(center=(screen_width // 2, screen_height // 2))
            screen.blit(text_surf, text_rect)

    pygame.display.flip() 
    pygame.time.Clock().tick(30) 

# --- Quit Pygame ---
if game_host:
    print("Stopping game host...")
    game_host.stop()
if game_client and game_client.is_connected: 
    print("Disconnecting game client...")
    game_client.disconnect()
pygame.quit()
