import pygame
import time # For simple non-blocking delay
from gui.lobby import LobbyScreen
from network.client import GameClient # Import GameClient

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

# --- Network Client ---
# Player name will be requested in UI or defaulted here
player_name_input = input("Enter your player name (default: PyPlayer): ") or f"PyPlayer{int(time.time())%100}"
game_client = GameClient(player_name=player_name_input) 

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

                elif isinstance(action, tuple) and action[0] == "connect_to_game":
                    if game_client.is_connected: # Check if already connected
                        lobby_screen.connection_status_message = "Already connected. Disconnect first?"
                        # Optionally, could auto-disconnect here and proceed with new connection
                    else:
                        _, host_ip, tcp_port = action
                        lobby_screen.connection_status_message = f"Connecting to {host_ip}:{tcp_port}..."
                        lobby_screen.current_player_list = [] # Clear player list before attempting new connection
                        pygame.display.flip() 

                        connection_successful = game_client.connect(host_ip, tcp_port, player_name_override=game_client.player_name)
                        
                        if connection_successful:
                            # Status message will be updated below based on is_connected state
                            pass
                        else:
                            lobby_screen.connection_status_message = f"Failed to connect to {host_ip}:{tcp_port}."
                            # Ensure client is fully reset if connect failed partway
                            if game_client.is_connected or game_client.tcp_socket: # is_connected should be false now
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
                # Avoid overriding "failed to connect" or "Refreshing" messages immediately
                if "Connecting to" not in lobby_screen.connection_status_message and \
                   "Refreshing" not in lobby_screen.connection_status_message:
                    lobby_screen.connection_status_message = "Disconnected. Select a game to connect."
        
        was_connected = is_connected_now


    # --- Drawing ---
    screen.fill(lobby_screen.colors["white"]) 

    if current_screen == "lobby":
        lobby_screen.draw(screen)

    pygame.display.flip() 

    pygame.time.Clock().tick(30) 

# --- Quit Pygame ---
if game_client and game_client.is_connected: # Ensure disconnection on exit
    game_client.disconnect()
pygame.quit()
