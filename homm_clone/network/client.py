import socket
import json
import time
import threading

DISCOVERY_PORT = 6000
MAX_BUFFER_SIZE = 4096 # For receiving messages

def send_message(sock, message_type, payload):
    """Helper function to send a JSON message."""
    try:
        if sock and sock.fileno() != -1: # Check if socket is valid
            message = json.dumps({"type": message_type, "payload": payload})
            sock.sendall(message.encode('utf-8'))
            print(f"Sent: {message_type}, {payload}") # Debug print
        else:
            print("Cannot send: Socket is not valid.")
    except socket.error as e:
        print(f"Socket error sending message ({message_type}): {e}")
    except Exception as e:
        print(f"Error sending message ({message_type}): {e}")

# def receive_message(sock): # Commented out as per previous subtask
#     # ... (old implementation) ...

class GameClient:
    def __init__(self, player_name="TestClient"):
        self.discovered_games = []
        self.tcp_socket = None
        self.server_address = None
        self.player_name = player_name 
        self.player_id = None
        self.player_list = []
        self.receive_buffer = b"" 
        
        self._listening_thread = None
        self._is_connected = False 
        self.lock = threading.Lock() 

    @property
    def is_connected(self):
        return self.tcp_socket is not None and self._is_connected

    def _parse_broadcast_message(self, data, addr):
        try:
            message = json.loads(data.decode('utf-8'))
            game_info = {
                "game_name": message.get("game_name"),
                "host_name": message.get("host_name"),
                "tcp_port": message.get("tcp_port"),
                "host_ip": addr[0] 
            }
            return game_info
        except json.JSONDecodeError:
            return None
        except Exception as e:
            print(f"An error occurred while parsing broadcast message: {e}")
            return None

    def listen_for_games(self, timeout=5.0):
        self.discovered_games = [] 
        udp_listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp_listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            udp_listener_socket.bind(('', DISCOVERY_PORT)) 
            print(f"Client listening for games on port {DISCOVERY_PORT}...")
        except socket.error as e:
            print(f"Failed to bind UDP listener socket: {e}")
            udp_listener_socket.close()
            return []
        udp_listener_socket.settimeout(1.0) 
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                data, addr = udp_listener_socket.recvfrom(1024) 
                game_info = self._parse_broadcast_message(data, addr)
                if game_info:
                    is_duplicate = False
                    for game in self.discovered_games:
                        if game["host_ip"] == game_info["host_ip"] and game["tcp_port"] == game_info["tcp_port"]:
                            is_duplicate = True; break
                    if not is_duplicate: self.discovered_games.append(game_info)
            except socket.timeout: continue
            except Exception as e: print(f"Error receiving broadcast: {e}")
        udp_listener_socket.close()
        return self.discovered_games

    def discover_games(self, timeout=5.0):
        return self.listen_for_games(timeout)

    def _listen_for_server_messages_thread(self):
        print("Listening for server messages thread started.")
        self.tcp_socket.settimeout(1.0) 

        was_connected_when_loop_started = self._is_connected
        
        while self._is_connected and self.tcp_socket:
            was_connected_when_loop_started = self._is_connected 

            try:
                data = self.tcp_socket.recv(MAX_BUFFER_SIZE)
                if not data:
                    print("Server connection closed (recv returned empty).")
                    if self._is_connected: self._is_connected = False
                    break 
                self.receive_buffer += data
            except socket.timeout:
                continue 
            except socket.error as e:
                print(f"Socket error during recv: {e}")
                if self._is_connected: self._is_connected = False
                break 
            except Exception as e: 
                print(f"Unexpected error during recv: {e}")
                if self._is_connected: self._is_connected = False
                break

            while self.receive_buffer:
                try:
                    _ = self.receive_buffer.decode('utf-8') # Check for early decode error
                except UnicodeDecodeError as ude:
                    print(f"UnicodeDecodeError in buffer: {ude}. Buffer (partial): {self.receive_buffer[:100]}")
                    next_brace_index = self.receive_buffer.find(b'{')
                    if next_brace_index != -1:
                        print(f"Discarding {next_brace_index} bytes due to UnicodeDecodeError.")
                        self.receive_buffer = self.receive_buffer[next_brace_index:]
                    else:
                        print("No '{' found after UnicodeDecodeError, clearing buffer.")
                        self.receive_buffer = b"" 
                    break 

                start_brace_index = -1
                brace_count = 0
                end_brace_index = -1
                for i, char_code in enumerate(self.receive_buffer): 
                    char = chr(char_code) 
                    if char == '{':
                        if start_brace_index == -1: start_brace_index = i
                        brace_count += 1
                    elif char == '}':
                        if start_brace_index != -1: 
                            brace_count -= 1
                            if brace_count == 0:
                                end_brace_index = i; break 
                
                if start_brace_index != -1 and end_brace_index != -1 and brace_count == 0:
                    message_bytes = self.receive_buffer[start_brace_index : end_brace_index + 1]
                    try:
                        msg_str = message_bytes.decode('utf-8')
                        msg = json.loads(msg_str)
                        print(f"Parsed message: {msg_str}") 

                        msg_type = msg.get("type")
                        payload = msg.get("payload")

                        if msg_type == "player_list_update":
                            with self.lock:
                                self.player_list = payload.get("players", [])
                            print(f"\n--- Player List Updated (Thread) ---")
                            for player in self.player_list:
                                # MODIFICATION FOR STEP 1a
                                print(f"  ID: {player.get('id')}, Name: {player.get('name')}, Ready: {player.get('is_ready')}")
                            print("----------------------------------\n")
                        elif msg_type == "join_ack":
                            print(f"Received unexpected JOIN_ACKNOWLEDGEMENT in listener: {payload}")
                        elif msg_type == "error":
                            print(f"Error from server: {payload.get('message')}")
                        else:
                            print(f"Received unhandled message from server: Type={msg_type}, Payload={payload}")

                        self.receive_buffer = self.receive_buffer[end_brace_index + 1:]
                        continue 
                    except json.JSONDecodeError as je:
                        print(f"JSONDecodeError: {je}. Problematic part: {message_bytes.decode('utf-8', errors='replace')}")
                        self.receive_buffer = self.receive_buffer[end_brace_index + 1:]
                        print(f"Discarded problematic JSON. Remaining buffer: {len(self.receive_buffer)}")
                        continue 
                    except UnicodeDecodeError as ude_msg: 
                        print(f"UnicodeDecodeError for specific message: {ude_msg}. Message bytes: {message_bytes}")
                        self.receive_buffer = self.receive_buffer[end_brace_index + 1:]
                        continue
                else: 
                    break 
        print("Server message listening thread stopped.")
        if self.tcp_socket and was_connected_when_loop_started:
            print("Server message listener: Cleaning up connection (thread end).")
            self.disconnect(server_initiated=True, called_from_listener_thread=True)

    def connect_to_host(self, host_ip, tcp_port, player_name_to_send=None):
        if self.tcp_socket and self._is_connected: 
            print("Already connected. Please disconnect first.")
            return False
        self.player_name = player_name_to_send or self.player_name 
        self.receive_buffer = b"" 
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Attempting to connect to {host_ip}:{tcp_port}...")
            self.tcp_socket.connect((host_ip, tcp_port))
            self.server_address = (host_ip, tcp_port)
            print(f"TCP connection established with {self.server_address}. Sending JOIN_REQUEST...")
            join_payload = {"name": self.player_name}
            send_message(self.tcp_socket, "join_request", join_payload)
            
            ack_msg_json = None 
            try:
                self.tcp_socket.settimeout(5.0) 
                temp_buffer = b""
                while True: 
                    chunk = self.tcp_socket.recv(MAX_BUFFER_SIZE)
                    if not chunk: raise socket.error("Connection closed while waiting for JOIN_ACK")
                    temp_buffer += chunk
                    try:
                        temp_buffer_str = temp_buffer.decode('utf-8')
                        s_idx = temp_buffer_str.find('{')
                        e_idx = -1
                        if s_idx != -1:
                            bal = 0
                            for i in range(s_idx, len(temp_buffer_str)):
                                if temp_buffer_str[i] == '{': bal += 1
                                elif temp_buffer_str[i] == '}': bal -=1
                                if bal == 0: e_idx = i; break 
                        if s_idx != -1 and e_idx != -1:
                            ack_str = temp_buffer_str[s_idx : e_idx+1]
                            ack_msg_json = json.loads(ack_str)
                            remaining_bytes = temp_buffer_str[e_idx+1:].encode('utf-8')
                            self.receive_buffer += remaining_bytes 
                            break 
                        elif len(temp_buffer) > MAX_BUFFER_SIZE * 2: 
                            raise socket.error("JOIN_ACK too long or not found")
                    except json.JSONDecodeError:
                        if len(temp_buffer) > MAX_BUFFER_SIZE * 2: 
                            raise socket.error("Error decoding JOIN_ACK or message too large")
                        continue 
                    except UnicodeDecodeError:
                         if len(temp_buffer) > MAX_BUFFER_SIZE * 2:
                            raise socket.error("Unicode error in JOIN_ACK")
                         continue 
            finally:
                if self.tcp_socket: self.tcp_socket.settimeout(1.0) 
            ack_msg = ack_msg_json 
            if ack_msg and ack_msg.get("type") == "join_ack": 
                payload = ack_msg.get("payload", {})
                self.player_id = payload.get("player_id")
                with self.lock:
                    self.player_list = payload.get("player_list", [])
                self._is_connected = True 
                print(f"Successfully joined game. Player ID: {self.player_id}")
                
                # MODIFICATION FOR STEP 1b
                print("--- Initial Player List (from JOIN_ACK) ---")
                if self.player_list:
                    for player_info in self.player_list:
                        print(f"  ID: {player_info.get('id')}, Name: {player_info.get('name')}, Ready: {player_info.get('is_ready')}")
                else:
                    print("  (empty)")
                print("-------------------------------------------")
                # Old print line: print(f"Initial player list: {self.player_list}") # This can be removed or kept

                self._listening_thread = threading.Thread(target=self._listen_for_server_messages_thread, daemon=True)
                self._listening_thread.start()
                return True
            else:
                error_msg = f"Failed to join game. Ack not received or invalid. Msg: {ack_msg}"
                if ack_msg and ack_msg.get("type") == "error":
                    error_msg = f"Failed to join game. Server error: {ack_msg.get('payload', {}).get('message')}"
                print(error_msg)
                if self.tcp_socket: self.tcp_socket.close()
                self.tcp_socket = None; self._is_connected = False 
                return False
        except socket.error as e:
            print(f"Socket error during connect/join: {e}")
            if self.tcp_socket: self.tcp_socket.close() 
            self.tcp_socket = None; self._is_connected = False
            return False
        except Exception as e: 
            print(f"An unexpected error occurred during connection/join: {e}")
            if self.tcp_socket: self.tcp_socket.close()
            self.tcp_socket = None; self._is_connected = False
            return False

    def connect(self, host_ip, port, player_name_override=None):
        return self.connect_to_host(host_ip, port, player_name_to_send=player_name_override)

    def disconnect(self, server_initiated=False, called_from_listener_thread=False):
        if not self.tcp_socket and not self._is_connected: return
        print(f"Disconnecting from {self.server_address if self.server_address else 'unknown server'} (server_initiated={server_initiated}, called_from_listener={called_from_listener_thread})...")
        self._is_connected = False 
        temp_socket = self.tcp_socket
        self.tcp_socket = None 
        if temp_socket:
            if not server_initiated and self.player_id: pass
            try:
                temp_socket.close()
                print(f"Socket closed.")
            except socket.error as e: print(f"Error closing socket: {e}")
        if self._listening_thread and self._listening_thread.is_alive() and not called_from_listener_thread:
            self._listening_thread.join(timeout=1.0) 
        self.player_id = None
        print(f"Client disconnected state processed.")

    def send_ready_state(self, is_ready):
        if not self.is_connected:
            print("Cannot send ready state: Not connected.")
            return
        payload = {"is_ready": is_ready}
        send_message(self.tcp_socket, "set_ready_state", payload)
        print(f"Sent 'set_ready_state' message with payload: {payload}")

if __name__ == '__main__':
    default_name = f"Player{int(time.time())%1000}"
    client_name = input(f"Enter your name (e.g., {default_name}): ") or default_name
    client = GameClient(player_name=client_name)
    print("Starting game discovery...")
    games_found = client.discover_games(timeout=3.0) 
    if not games_found: print("No games found.")
    else:
        print("\nAvailable games:")
        for i, game in enumerate(games_found):
            print(f"{i+1}. Game: {game['game_name']}, Host: {game['host_name']} at {game['host_ip']}:{game['tcp_port']}")
        try:
            choice_str = input(f"Select game to join (1-{len(games_found)}), or 0 to skip: ")
            if not choice_str: print("No game selected. Exiting.")
            else:
                choice = int(choice_str) -1
                if choice == -1: print("Skipping connection. Exiting.")
                elif 0 <= choice < len(games_found):
                    selected_game = games_found[choice]
                    print(f"\nAttempting to connect to: {selected_game['game_name']} (Host: {selected_game['host_name']}) at {selected_game['host_ip']}:{selected_game['tcp_port']} as {client.player_name}...")
                    if client.connect(selected_game['host_ip'], selected_game['tcp_port']):
                        print("Connection and join successful! Listening for updates...")
                        print("Player list should appear in the GUI if running main.py.")
                        print("This console will show direct client messages.")
                        print("Press Ctrl+C to disconnect and exit this client's script.")
                        try:
                            while client.is_connected: time.sleep(1)
                        except KeyboardInterrupt: print("\nDisconnecting due to user request (Ctrl+C)...")
                        finally: client.disconnect()
                    else: print("Connection or join failed.")
                else: print("Invalid selection.")
        except ValueError: print("Invalid input.")
    print(f"Client script for '{client.player_name}' finished.")
