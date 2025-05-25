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

def receive_message(sock):
    """Helper function to receive a JSON message."""
    try:
        if sock and sock.fileno() != -1: # Check if socket is valid
            # Simplified receive, assumes one JSON message per recv call for now
            data = sock.recv(MAX_BUFFER_SIZE)
            if not data:
                print("Receive: Connection closed by server (no data).")
                return None # Connection closed
            
            decoded_data = data.decode('utf-8')
            print(f"Received raw: {decoded_data}") # Debug print
            return json.loads(decoded_data)
        else:
            print("Cannot receive: Socket is not valid.")
            return None
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e} - Data: {data if 'data' in locals() else 'N/A'}")
        return None
    except socket.timeout:
        print("Receive: Socket timeout.") # Expected if socket has timeout set
        return None
    except socket.error as e:
        print(f"Socket error during receive: {e}")
        return None 
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None

class GameClient:
    def __init__(self, player_name="TestClient"):
        self.discovered_games = []
        self.tcp_socket = None
        self.server_address = None
        self.player_name = player_name # Added player_name
        self.player_id = None
        self.player_list = []
        
        self._listening_thread = None
        self._is_connected = False # True after JOIN_ACK is successful
        self.lock = threading.Lock() # For self.player_list or other shared states

    @property
    def is_connected(self):
        """True if the client has successfully joined a game and TCP socket is active."""
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
            # print(f"Error decoding JSON from broadcast {addr}") # Can be noisy
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
        # print(f"Stopped listening. Found {len(self.discovered_games)} game(s).")
        return self.discovered_games

    def discover_games(self, timeout=5.0):
        return self.listen_for_games(timeout)

    def _listen_for_server_messages_thread(self):
        print("Listening for server messages thread started.")
        while self._is_connected and self.tcp_socket:
            msg = receive_message(self.tcp_socket)
            if msg is None:
                print("Server connection lost or socket closed.")
                print("Server message listener: Connection lost or socket closed.")
                # self._is_connected should be False already if receive_message returned None due to socket error/closure
                # but if it's due to _is_connected being set False elsewhere (e.g. disconnect()), this is fine.
                if self._is_connected: # if it was true, set it false
                    self._is_connected = False
                break # Exit thread

            msg_type = msg.get("type")
            payload = msg.get("payload")

            if msg_type == "player_list_update":
                with self.lock:
                    self.player_list = payload.get("players", [])
                print(f"\n--- Player List Updated ---")
                for player in self.player_list:
                    print(f"  ID: {player.get('id')}, Name: {player.get('name')}")
                print("---------------------------\n")
            elif msg_type == "join_ack": # Should ideally be handled in connect, but good to log if seen here
                print(f"Received unexpected JOIN_ACKNOWLEDGEMENT: {payload}")
            elif msg_type == "error":
                 print(f"Error from server: {payload.get('message')}")
            else:
                print(f"Received unhandled message from server: Type={msg_type}, Payload={payload}")
        
        print("Server message listening thread stopped.")
        # If loop exits, means connection is likely down. 
        # Call disconnect only if it was an unexpected closure.
        # server_initiated helps prevent re-sending leave messages or double-closing.
        print(f"Server message listening thread stopped. self._is_connected is {self._is_connected}")
        if self.tcp_socket and self._is_connected: # If socket still exists and we thought we were connected
            print("Server message listener: Connection seems to have dropped unexpectedly.")
            self.disconnect(server_initiated=True) 


    def connect_to_host(self, host_ip, tcp_port, player_name_to_send=None):
        if self.tcp_socket and self._is_connected: # Check _is_connected as well
            print("Already connected. Please disconnect first.")
            return False

        self.player_name = player_name_to_send or self.player_name # Use provided or default

        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print(f"Attempting to connect to {host_ip}:{tcp_port}...")
            self.tcp_socket.connect((host_ip, tcp_port))
            self.server_address = (host_ip, tcp_port)
            # Do not set _is_connected = True here. Set it only after successful JOIN_ACK.
            print(f"TCP connection established with {self.server_address}. Sending JOIN_REQUEST...")

            # Send JOIN_REQUEST
            join_payload = {"name": self.player_name}
            send_message(self.tcp_socket, "join_request", join_payload)

            # Wait for JOIN_ACKNOWLEDGEMENT
            ack_msg = receive_message(self.tcp_socket)
            if ack_msg and ack_msg.get("type") == "join_ack":
                payload = ack_msg.get("payload", {})
                self.player_id = payload.get("player_id")
                with self.lock:
                    self.player_list = payload.get("player_list", [])
                self._is_connected = True # Successfully joined!
                print(f"Successfully joined game. Player ID: {self.player_id}")
                print(f"Initial player list: {self.player_list}")

                # Start listening thread
                self._listening_thread = threading.Thread(target=self._listen_for_server_messages_thread, daemon=True)
                self._listening_thread.start()
                return True
            else:
                # Join failed or server sent unexpected message
                error_msg = f"Failed to join game. Ack not received or invalid. Msg: {ack_msg}"
                if ack_msg and ack_msg.get("type") == "error":
                    error_msg = f"Failed to join game. Server error: {ack_msg.get('payload', {}).get('message')}"
                print(error_msg)
                if self.tcp_socket:
                    self.tcp_socket.close()
                self.tcp_socket = None
                self._is_connected = False # Ensure this is false
                return False

        except socket.error as e:
            print(f"Socket error during connect/join: {e}")
            if self.tcp_socket: self.tcp_socket.close() # Ensure socket is closed
            self.tcp_socket = None
            self._is_connected = False
            return False
        except Exception as e: 
            print(f"An unexpected error occurred during connection/join: {e}")
            if self.tcp_socket: self.tcp_socket.close()
            self.tcp_socket = None
            self._is_connected = False
            return False


    def connect(self, host_ip, port, player_name_override=None):
        return self.connect_to_host(host_ip, port, player_name_to_send=player_name_override)

    def disconnect(self, server_initiated=False):
        # Check if there's anything to disconnect from
        if not self.tcp_socket and not self._is_connected:
            # print("Client already disconnected.") # Can be noisy
            return

        print(f"Disconnecting from {self.server_address if self.server_address else 'unknown server'}...")
        
        # Signal listening thread to stop and update connection state
        # This order helps prevent race conditions where listening thread might try to use a closing socket
        self._is_connected = False 

        temp_socket = self.tcp_socket
        self.tcp_socket = None # Prevent further use of the socket

        if temp_socket:
            if not server_initiated and self.player_id:
                # print(f"Sending LEAVE_REQUEST for player {self.player_id}") # Debug
                # send_message(temp_socket, "leave_request", {"player_id": self.player_id}) # Send if implemented fully
                pass # For now, client just closes connection

            try:
                # Attempt a graceful shutdown of the socket
                # temp_socket.shutdown(socket.SHUT_RDWR) # Can cause errors if socket already dead
                temp_socket.close()
                print(f"Socket closed.")
            except socket.error as e:
                print(f"Error closing socket: {e}")
        
        if self._listening_thread and self._listening_thread.is_alive():
            # print("Waiting for listening thread to stop...")
            self._listening_thread.join(timeout=1.0) # Reduced timeout
            # if self._listening_thread.is_alive():
            #    print("Listening thread did not stop in time.")
        
        self.player_id = None
        # Do not clear player_list here, main.py will do it based on connection status
        # This allows UI to show last known list on unexpected disconnect.
        print(f"Client disconnected state processed.")


if __name__ == '__main__':
    default_name = f"Player{int(time.time())%1000}"
    client_name = input(f"Enter your name (e.g., {default_name}): ") or default_name
    client = GameClient(player_name=client_name)
    
    print("Starting game discovery...")
    games_found = client.discover_games(timeout=3.0) 
    
    if not games_found:
        print("No games found.")
    else:
        print("\nAvailable games:")
        for i, game in enumerate(games_found):
            print(f"{i+1}. Game: {game['game_name']}, Host: {game['host_name']} at {game['host_ip']}:{game['tcp_port']}")
        
        try:
            choice_str = input(f"Select game to join (1-{len(games_found)}), or 0 to skip: ")
            if not choice_str: # User pressed Enter
                print("No game selected. Exiting.")
            else:
                choice = int(choice_str) -1
                if choice == -1: # User entered 0
                     print("Skipping connection. Exiting.")
                elif 0 <= choice < len(games_found):
                    selected_game = games_found[choice]
                    print(f"\nAttempting to connect to: {selected_game['game_name']} (Host: {selected_game['host_name']}) at {selected_game['host_ip']}:{selected_game['tcp_port']} as {client.player_name}...")
                    
                    if client.connect(selected_game['host_ip'], selected_game['tcp_port']):
                        print("Connection and join successful! Listening for updates...")
                        print("Player list should appear in the GUI if running main.py.")
                        print("This console will show direct client messages.")
                        print("Press Ctrl+C to disconnect and exit this client's script.")
                        try:
                            while client.is_connected: # Use the new property
                                time.sleep(1)
                        except KeyboardInterrupt:
                            print("\nDisconnecting due to user request (Ctrl+C)...")
                        finally:
                            client.disconnect()
                    else:
                        print("Connection or join failed.")
                else:
                    print("Invalid selection.")
        except ValueError:
            print("Invalid input.")
            
    print(f"Client script for '{client.player_name}' finished.")
