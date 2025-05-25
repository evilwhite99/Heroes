import pygame
import time # For simple non-blocking delay
from gui.lobby import LobbyScreen
from network.client import GameClient # Import GameClient
from network.host import GameHost # Import GameHost

# Initialize Pygame
pygame.init()

# Set screen dimensions
screen_width = 1000 # Increased width to better accommodate UI
screen_height = 700 # Increased height
screen = pygame.display.set_mode((screen_width, screen_height))

# Set window title
pygame.display.set_caption("HoMM Clone - Lobby")

# --- Game State ---
current_screen = "lobby"  # Can be "lobby", "game", "loading", etc.

# --- Network Client & Host ---
# Player name will be requested in UI or defaulted here
player_name_input = input("Enter your player name (default: PyPlayer): ") or f"PyPlayer{int(time.time())%100}"
game_client = GameClient(player_name=player_name_input) 
game_host = None # Initialize game_host

# --- Lobby Screen Instance ---
lobby_screen = LobbyScreen(screen)

# --- Initial Game Discovery ---
lobby_screen.connection_status_message = "Searching for games..."
lobby_screen.discovered_games = game_client.discover_games(timeout=2.0) 
if not lobby_screen.discovered_games:
    lobby_screen.connection_status_message = "No games found. Click Refresh."
else:
    lobby_screen.connection_status_message = f"Found {len(lobby_screen.discovered_games)} game(s). Select one to connect."


# --- Main Game Loop ---
running = True
was_connected = False # To track connection state changes for status messages

while running:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            if game_client and game_client.is_connected: # Use property
                game_client.disconnect() 

        if current_screen == "lobby":
            action = lobby_screen.handle_event(event, game_client) 
            if action:
                if action == "refresh_games":
                    lobby_screen.connection_status_message = "Refreshing games..."
                    lobby_screen.current_player_list = [] # Clear player list on refresh
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

                        game_host = GameHost(host_name=f"{game_client.player_name}'s Game", tcp_port=5555) # Default port
                        game_host.start()
                        time.sleep(0.5) # Allow host to initialize

                        lobby_screen.connection_status_message = "Connecting to local game..."
                        pygame.display.flip()
                        
                        # Use the host's actual configured port if it could change
                        # For now, assuming 5555 is fixed for this direct connection.
                        connection_successful = game_client.connect("127.0.0.1", game_host.tcp_port, player_name_override=game_client.player_name)

                        if connection_successful:
                            lobby_screen.connection_status_message = f"Now hosting on port {game_host.tcp_port}. You are in the lobby."
                            lobby_screen.is_hosting = True # Set hosting flag in UI
                            lobby_screen.discovered_games = [] # Clear discovered games
                            lobby_screen.selected_game_index = None # Clear selection
                        else:
                            lobby_screen.connection_status_message = "Failed to connect client to local host."
                            if game_host: # Ensure host is stopped if client can't connect to it
                                game_host.stop()
                                game_host = None
                            lobby_screen.is_hosting = False # Ensure flag is false on failure
                
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
                        
                        if connection_successful:
                            pass # Status message updated below
                        else:
                            lobby_screen.connection_status_message = f"Failed to connect to {host_ip}:{tcp_port}."
                            if game_client.is_connected or game_client.tcp_socket:
                                 game_client.disconnect()


    # --- Update GUI from GameClient State (Lobby specific) ---
    if current_screen == "lobby":
        is_connected_now = game_client.is_connected # Use the property

        if is_connected_now:
            with game_client.lock: # Access game_client.player_list safely
                 lobby_screen.current_player_list = list(game_client.player_list) # Update with a copy
            
            if not was_connected: # Just connected
                selected_game_name = "the game"
                if lobby_screen.selected_game_index is not None and \
                   lobby_screen.selected_game_index < len(lobby_screen.discovered_games):
                     selected_game_details = lobby_screen.discovered_games[lobby_screen.selected_game_index]
                     selected_game_name = selected_game_details.get('game_name', 'the game')
                lobby_screen.connection_status_message = f"Successfully connected to {selected_game_name} as {game_client.player_name} (ID: {game_client.player_id})!"
        else: # Not connected
            lobby_screen.current_player_list = [] # Clear player list if not connected
            if was_connected: # Just disconnected
                status_msg_prefix = "Disconnected."
                if game_host: # If we were hosting
                    print("Client disconnected while hosting. Stopping host.")
                    game_host.stop()
                    game_host = None
                    lobby_screen.is_hosting = False
                    status_msg_prefix = "Host stopped."
                
                # Avoid overriding "failed to connect" or "Refreshing" messages immediately
                if "Connecting to" not in lobby_screen.connection_status_message and \
                   "Refreshing" not in lobby_screen.connection_status_message and \
                   "Failed to connect" not in lobby_screen.connection_status_message:
                    lobby_screen.connection_status_message = f"{status_msg_prefix} Select a game or host."
                    # Optionally, trigger auto-refresh of games list here
                    # lobby_screen.discovered_games = game_client.discover_games(timeout=1.0)
                    # lobby_screen.connection_status_message += f" Found {len(lobby_screen.discovered_games)} games."

        was_connected = is_connected_now


    # --- Drawing ---
    screen.fill(lobby_screen.colors["white"]) 

    if current_screen == "lobby":
        lobby_screen.draw(screen)

    pygame.display.flip() 

    pygame.time.Clock().tick(30) 

# --- Quit Pygame ---
if game_host:
    print("Stopping game host...")
    game_host.stop()
if game_client and game_client.is_connected: # Ensure disconnection on exit
    print("Disconnecting game client...")
    game_client.disconnect()
pygame.quit()
