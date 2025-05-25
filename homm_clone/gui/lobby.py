import pygame

# Data Structures for Factions and Starting Locations
FACTIONS = [
    {"name": "Castle", "color": (200, 200, 200), "hover_color": (230, 230, 230)}, # Light Grey
    {"name": "Rampart", "color": (100, 150, 100), "hover_color": (130, 180, 130)}, # Forest Green
    {"name": "Tower", "color": (100, 100, 200), "hover_color": (130, 130, 230)}, # Light Blue
    {"name": "Inferno", "color": (200, 100, 100), "hover_color": (230, 130, 130)}, # Light Red
    {"name": "Necropolis", "color": (160, 160, 160), "hover_color": (190, 190, 190)}, # Dark Grey
    {"name": "Dungeon", "color": (150, 100, 150), "hover_color": (180, 130, 180)}, # Purple
]

STARTING_LOCATIONS = [
    {"id": "slot_1", "name": "Position 1", "color": (255, 0, 0), "hover_color": (255, 80, 80)},
    {"id": "slot_2", "name": "Position 2", "color": (0, 255, 0), "hover_color": (80, 255, 80)},
    {"id": "slot_3", "name": "Position 3", "color": (0, 0, 255), "hover_color": (80, 80, 255)},
    {"id": "slot_4", "name": "Position 4", "color": (255, 255, 0), "hover_color": (255, 255, 80)},
]

class LobbyScreen:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 30) 
        self.small_font = pygame.font.Font(None, 24)
        self.title_font = pygame.font.Font(None, 36)

        self.screen_width = screen.get_width()
        self.screen_height = screen.get_height()

        self.colors = {
            "white": (255, 255, 255), "black": (0, 0, 0), "grey": (200, 200, 200),
            "light_blue": (210, 230, 250), # Changed for Faction area bg
            "light_green": (210, 250, 210), # Changed for Map/Game Discovery area bg
            "light_red": (250, 210, 210),   # Changed for Player list area bg
            "dark_grey": (100, 100, 100),
            "button_color": (150, 150, 150), "button_hover": (180, 180, 180),
            "text_color": (10, 10, 10), # Darker text
            "highlight_color": (255, 215, 0), # Gold highlight for selections
            "border_color": (50, 50, 50) # Darker border for highlighted items
        }

        # Section Rects
        self.faction_rect_width = self.screen_width * 0.2
        self.faction_rect = pygame.Rect(0, 0, self.faction_rect_width, self.screen_height)
        
        self.map_rect_width = self.screen_width * 0.5
        self.map_rect_x = self.faction_rect_width
        self.map_rect = pygame.Rect(self.map_rect_x, 0, self.map_rect_width, self.screen_height)
        
        self.player_rect_width = self.screen_width * 0.3
        self.player_rect_x = self.faction_rect_width + self.map_rect_width
        self.player_rect = pygame.Rect(self.player_rect_x, 0, self.player_rect_width, self.screen_height)

        # Game discovery and connection attributes
        self.discovered_games = []
        self.selected_game_index = None
        self.connection_status_message = "Initializing..."
        self.current_player_list = []
        
        # Faction and Starting Location attributes
        self.available_factions = FACTIONS
        self.available_starting_locations = STARTING_LOCATIONS
        self.selected_faction_index = None
        self.selected_location_index = None
        self.is_hosting = False # Added is_hosting flag
        self.local_player_is_ready = False # Added local_player_is_ready flag

        # UI element properties for factions and locations
        self.faction_item_height = 40
        self.faction_list_start_y = self.faction_rect.y + 60
        self.location_item_height = 40
        self.location_list_start_y = self.map_rect.y + 60 # Will be below game list
        
        # Player list display properties
        self.player_list_start_y = self.player_rect.y + 60
        self.player_item_height = 30

        self.faction_display_rects = [] # For click detection
        self.location_display_rects = [] # For click detection
        
        # Common properties for buttons in the player panel
        button_width_player_panel = self.player_rect.width - 40 
        button_height_player_panel = 40 # Consistent height
        player_panel_button_center_x = self.player_rect.x + self.player_rect.width // 2
        
        toggle_ready_button_y = self.screen_height - 120 # Positioned higher
        toggle_ready_button_x = player_panel_button_center_x - button_width_player_panel // 2
        toggle_ready_rect = pygame.Rect(toggle_ready_button_x, toggle_ready_button_y, button_width_player_panel, button_height_player_panel)

        start_game_button_y = toggle_ready_rect.bottom + 10 
        start_game_button_x = player_panel_button_center_x - button_width_player_panel // 2
        start_game_rect = pygame.Rect(start_game_button_x, start_game_button_y, button_width_player_panel, button_height_player_panel)

        self.buttons = {
            "host_game": {
                "rect": pygame.Rect(self.map_rect_x + 20, self.screen_height - 170, 200, 40),
                "text": "Host New Game", 
                "action": "host_game"
            },
            "refresh_games": {
                "rect": pygame.Rect(self.map_rect_x + 20, self.screen_height - 120, 200, 40),
                "text": "Refresh Games", "action": "refresh_games"
            },
            "connect_selected": {
                "rect": pygame.Rect(self.map_rect_x + 20, self.screen_height - 70, 250, 40), 
                "text": "Connect to Selected Game", "action": "connect_selected"
            },
            "toggle_ready": {
              "rect": toggle_ready_rect, # Use the calculated rect
              "text": "Ready", 
              "action": "toggle_ready_state"
            },
            "start_game": {
              "rect": start_game_rect, # Use the calculated rect
              "text": "Start Game",
              "action": "initiate_game_start"
            }
        }
        self.game_item_height = 30
        self.games_list_start_y = self.map_rect.y + 60 # Title for "Available Games" is at 20, list starts at 60
        # Adjust starting Y for locations to be below games list
        self.max_games_display_height = self.screen_height * 0.4 # e.g. 40% of map_rect for games
        self.location_list_start_y = self.games_list_start_y + self.max_games_display_height + 20 # Add padding


    def _draw_text(self, text, font, color, surface, x, y, center_x_of_rect=None, center_y_of_rect=None, top_left_of_rect=None):
        text_obj = font.render(text, True, color)
        text_rect = text_obj.get_rect()
        if center_x_of_rect: text_rect.centerx = center_x_of_rect.centerx
        else: text_rect.x = x
        if center_y_of_rect: text_rect.centery = center_y_of_rect.centery
        else: text_rect.y = y
        if top_left_of_rect: text_rect.topleft = top_left_of_rect.topleft
        surface.blit(text_obj, text_rect)
        return text_rect

    def draw(self, screen):
        screen.fill(self.colors["white"])

        # --- Faction Selection Area ---
        pygame.draw.rect(screen, self.colors["light_blue"], self.faction_rect)
        self._draw_text("Factions", self.title_font, self.colors["text_color"], screen, 0, 20, center_x_of_rect=self.faction_rect)
        
        self.faction_display_rects = []
        faction_y_offset = self.faction_list_start_y
        for i, faction in enumerate(self.available_factions):
            item_rect = pygame.Rect(self.faction_rect.x + 10, faction_y_offset, self.faction_rect.width - 20, self.faction_item_height)
            self.faction_display_rects.append(item_rect)
            
            is_selected = (i == self.selected_faction_index)
            color_to_use = faction["color"]
            
            pygame.draw.rect(screen, color_to_use, item_rect)
            if is_selected:
                pygame.draw.rect(screen, self.colors["highlight_color"], item_rect, 3) # Gold border for selected

            self._draw_text(faction["name"], self.font, self.colors["text_color"], screen, 0,0, 
                              center_x_of_rect=item_rect, center_y_of_rect=item_rect)
            faction_y_offset += self.faction_item_height + 5

        # --- Map Preview / Game Discovery & Starting Location Area ---
        pygame.draw.rect(screen, self.colors["light_green"], self.map_rect)
        
        if not self.is_hosting:
            self._draw_text("Available Games", self.title_font, self.colors["text_color"], screen, 0, 20, center_x_of_rect=self.map_rect)
            # Display Discovered Games
            game_y_offset = self.games_list_start_y
            self.game_display_rects = [] 
            for i, game in enumerate(self.discovered_games):
                game_text = f"{game.get('game_name', 'N/A')} ({game.get('host_name', 'Unknown')})" # Simpler text
                item_rect = pygame.Rect(self.map_rect.x + 20, game_y_offset, self.map_rect.width - 40, self.game_item_height)
                self.game_display_rects.append(item_rect)

                if i == self.selected_game_index:
                    pygame.draw.rect(screen, self.colors["highlight_color"], item_rect)
                else: # Draw a light border for non-selected games for better UI
                    pygame.draw.rect(screen, self.colors["grey"], item_rect, 1)
                
                self._draw_text(game_text, self.small_font, self.colors["text_color"], screen, item_rect.x + 5, item_rect.y + (self.game_item_height - self.small_font.get_height()) // 2)
                game_y_offset += self.game_item_height + 5 
                if game_y_offset > self.games_list_start_y + self.max_games_display_height - self.game_item_height: break
        else: # We are hosting
            self.game_display_rects = [] # Clear game rects if hosting
            self._draw_text("Currently Hosting Game", self.title_font, self.colors["text_color"], screen, 0, 20, center_x_of_rect=self.map_rect)
            # Optionally, display host-specific info here like IP, port, etc.
            host_info_font = pygame.font.Font(None, 28)
            self._draw_text(f"Your game is being broadcast.", host_info_font, self.colors["dark_grey"], screen, 0, self.games_list_start_y, center_x_of_rect=self.map_rect)


        # Display Starting Locations (below game list or host info)
        title_x = self.map_rect.x + (self.map_rect.width // 2) - self.title_font.render("Starting Positions", True, self.colors["text_color"]).get_width() // 2
        self._draw_text("Starting Positions", self.title_font, self.colors["text_color"], screen, 
                          title_x, self.location_list_start_y - 40) 

        self.location_display_rects = []
        location_y_offset = self.location_list_start_y
        location_item_width = (self.map_rect.width - 40 - (len(self.available_starting_locations)-1)*10) / len(self.available_starting_locations)
        location_item_width = max(50, location_item_width) # Ensure minimum width
        current_x = self.map_rect.x + 20

        for i, loc in enumerate(self.available_starting_locations):
            item_rect = pygame.Rect(current_x, location_y_offset, location_item_width, self.location_item_height)
            self.location_display_rects.append(item_rect)
            
            is_selected = (i == self.selected_location_index)
            color_to_use = loc["color"]

            pygame.draw.rect(screen, color_to_use, item_rect)
            if is_selected:
                pygame.draw.rect(screen, self.colors["highlight_color"], item_rect, 3) # Gold border

            self._draw_text(loc["name"], self.small_font, self.colors["black"], screen, 0,0, 
                              center_x_of_rect=item_rect, center_y_of_rect=item_rect)
            current_x += location_item_width + 10


        # --- Player List Area ---
        pygame.draw.rect(screen, self.colors["light_red"], self.player_rect)
        self._draw_text("Players in Game", self.title_font, self.colors["text_color"], screen, 0, 20, center_x_of_rect=self.player_rect)
        
        player_y_offset = self.player_list_start_y
        if not self.current_player_list and "Connected" in self.connection_status_message :
             self._draw_text("No other players yet.", self.small_font, self.colors["text_color"], screen, 
                               self.player_rect.x + 15, player_y_offset)
        else:
            for i, player in enumerate(self.current_player_list):
                player_name = player.get("name", "Unknown Player")
                player_id = player.get("id", "N/A")
                is_ready = player.get("is_ready", False)
                player_text = f"ID: {player_id} - {player_name}{' [READY]' if is_ready else ''}"
                
                text_color = self.colors["highlight_color"] if is_ready else self.colors["text_color"]

                self._draw_text(player_text, self.small_font, text_color, screen, 
                                  self.player_rect.x + 15, player_y_offset)
                player_y_offset += self.player_item_height
                if player_y_offset > self.screen_height - 40: break

        # --- Buttons ---
        if not self.is_hosting:
            # Draw "Host New Game" button
            pygame.draw.rect(screen, self.colors["button_color"], self.buttons["host_game"]["rect"])
            self._draw_text(self.buttons["host_game"]["text"], self.font, self.colors["black"], screen, 0,0,
                              center_x_of_rect=self.buttons["host_game"]["rect"], center_y_of_rect=self.buttons["host_game"]["rect"])
            
            # Draw "Refresh Games" button
            pygame.draw.rect(screen, self.colors["button_color"], self.buttons["refresh_games"]["rect"])
            self._draw_text(self.buttons["refresh_games"]["text"], self.font, self.colors["black"], screen, 0,0,
                              center_x_of_rect=self.buttons["refresh_games"]["rect"], center_y_of_rect=self.buttons["refresh_games"]["rect"])

            # Draw "Connect to Selected Game" button
            if self.selected_game_index is not None and self.selected_game_index < len(self.discovered_games):
                pygame.draw.rect(screen, self.colors["button_color"], self.buttons["connect_selected"]["rect"])
                self._draw_text(self.buttons["connect_selected"]["text"], self.font, self.colors["black"], screen, 0,0,
                                  center_x_of_rect=self.buttons["connect_selected"]["rect"], center_y_of_rect=self.buttons["connect_selected"]["rect"])
        else: # We are hosting, maybe show a "Stop Hosting" or "Start Game" button later
            # For now, buttons related to joining/refreshing are hidden.
            pass # "Ready" button is drawn below, after this conditional block
        
        # Draw "Ready/Unready" button if connected or hosting
        if self.current_player_list or self.is_hosting: 
            ready_button_current_text = "Unready" if self.local_player_is_ready else "Ready"
            button_color_ready = self.colors["button_hover"] if self.local_player_is_ready else self.colors["button_color"]
            pygame.draw.rect(screen, button_color_ready, self.buttons["toggle_ready"]["rect"])
            self._draw_text(ready_button_current_text, self.font, self.colors["black"], screen, 0,0,
                              center_x_of_rect=self.buttons["toggle_ready"]["rect"], 
                              center_y_of_rect=self.buttons["toggle_ready"]["rect"])

            # Draw "Start Game" button if hosting
            if self.is_hosting:
                all_players_ready = False
                min_players_to_start = 1 
                if self.current_player_list and len(self.current_player_list) >= min_players_to_start:
                    all_players_ready = all(player.get("is_ready", False) for player in self.current_player_list)

                button_color_start = self.colors["button_color"] if all_players_ready else self.colors["dark_grey"]
                text_color_start = self.colors["black"] if all_players_ready else self.colors["grey"] 

                pygame.draw.rect(screen, button_color_start, self.buttons["start_game"]["rect"])
                self._draw_text(self.buttons["start_game"]["text"], self.font, text_color_start, screen, 0,0,
                                  center_x_of_rect=self.buttons["start_game"]["rect"],
                                  center_y_of_rect=self.buttons["start_game"]["rect"])


        self._draw_text(self.connection_status_message, self.small_font, self.colors["dark_grey"], screen, 
                          self.map_rect.x + 20, self.screen_height - 35)


    def handle_event(self, event, game_client_instance):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: 
                mouse_pos = event.pos
                
                # Check Faction clicks
                for i, rect in enumerate(self.faction_display_rects):
                    if rect.collidepoint(mouse_pos):
                        self.selected_faction_index = i
                        print(f"Selected faction: {self.available_factions[i]['name']}") # Debug
                        return None 

                # Check Starting Location clicks
                for i, rect in enumerate(self.location_display_rects):
                    if rect.collidepoint(mouse_pos):
                        self.selected_location_index = i
                        print(f"Selected location: {self.available_starting_locations[i]['name']}") # Debug
                        return None

                # Check game selection clicks
                if not self.is_hosting: # Only allow game selection if not hosting
                    for i, rect in enumerate(self.game_display_rects):
                        if rect.collidepoint(mouse_pos):
                            self.selected_game_index = i
                            self.connection_status_message = f"Selected: {self.discovered_games[i].get('game_name', 'N/A')}"
                            return None 

                # Check button clicks
                if not self.is_hosting and self.buttons["host_game"]["rect"].collidepoint(mouse_pos):
                    self.connection_status_message = "Attempting to host game..." 
                    return "host_game"

                if not self.is_hosting and self.buttons["refresh_games"]["rect"].collidepoint(mouse_pos):
                    self.connection_status_message = "Refreshing games..."
                    return "refresh_games" 

                if (self.current_player_list or self.is_hosting) and \
                   self.buttons["toggle_ready"]["rect"].collidepoint(mouse_pos):
                    self.local_player_is_ready = not self.local_player_is_ready 
                    print(f"Local ready state toggled to: {self.local_player_is_ready}") 
                    return "toggle_ready_state" 

                if self.is_hosting and self.buttons["start_game"]["rect"].collidepoint(mouse_pos):
                    all_players_ready = False
                    min_players_to_start = 1 
                    if self.current_player_list and len(self.current_player_list) >= min_players_to_start:
                        all_players_ready = all(player.get("is_ready", False) for player in self.current_player_list)
                    
                    if all_players_ready:
                        return "initiate_game_start"
                    else:
                        self.connection_status_message = "All players must be ready to start."
                        return None 

                if not self.is_hosting and \
                   self.selected_game_index is not None and \
                   self.selected_game_index < len(self.discovered_games) and \
                   self.buttons["connect_selected"]["rect"].collidepoint(mouse_pos):
                    
                    selected_game_details = self.discovered_games[self.selected_game_index]
                    host_ip = selected_game_details.get("host_ip")
                    tcp_port = selected_game_details.get("tcp_port")
                    
                    if host_ip and tcp_port:
                        self.connection_status_message = f"Connecting to {selected_game_details.get('game_name')}..."
                        return ("connect_to_game", host_ip, tcp_port)
                    else:
                        self.connection_status_message = "Error: Game details missing for selection."
                        
        return None
```
