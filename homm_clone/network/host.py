import socket
import threading
import time
import json

DISCOVERY_PORT = 6000
BROADCAST_ADDR = "255.255.255.255" # Or use '<broadcast>'
MAX_BUFFER_SIZE = 4096 # For receiving messages

def send_message(sock, message_type, payload):
    """Helper function to send a JSON message."""
    try:
        message = json.dumps({"type": message_type, "payload": payload})
        sock.sendall(message.encode('utf-8'))
    except Exception as e:
        print(f"Error sending message: {e}")

def receive_message(sock):
    """Helper function to receive a JSON message."""
    try:
        # This is a simplified receive; for production, you'd handle message framing (e.g., length prefix)
        # to correctly receive larger or multiple JSON objects if they are sent back-to-back.
        data = sock.recv(MAX_BUFFER_SIZE)
        if not data:
            return None # Connection closed
        return json.loads(data.decode('utf-8'))
    except json.JSONDecodeError as e:
        print(f"JSON Decode Error: {e} - Data: {data}")
        return None
    except socket.error as e:
        print(f"Socket error during receive: {e}")
        return None # Socket error
    except Exception as e:
        print(f"Error receiving message: {e}")
        return None


class GameHost:
    def __init__(self, host_name="Player1sHost", tcp_port=5555):
        self.host_name = host_name
        self.tcp_port = tcp_port
        self.game_name = "My HoMM Game"
        
        # Store clients as dicts: {"id": player_id, "name": name, "socket": conn, "address": addr, "thread": thread_obj}
        self.connected_clients = [] 
        self.next_player_id = 1 # Host can be player 0 or handle differently

        self._broadcasting = False
        self._tcp_server_running = False
        self._broadcast_thread = None
        self._tcp_server_thread = None
        
        self.udp_socket = None
        self.tcp_socket = None
        self.lock = threading.Lock() # To protect shared resources like connected_clients

    def _broadcast_message(self):
        message_data = {
            "game_name": self.game_name,
            "host_name": self.host_name,
            "tcp_port": self.tcp_port
        }
        message_bytes = json.dumps(message_data).encode('utf-8')
        
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        print(f"Starting UDP broadcast on port {DISCOVERY_PORT}...")
        while self._broadcasting:
            try:
                self.udp_socket.sendto(message_bytes, (BROADCAST_ADDR, DISCOVERY_PORT))
            except Exception as e:
                print(f"Error sending broadcast: {e}") # Handle case where network interface might go down
            time.sleep(2) 
        self.udp_socket.close()
        print("UDP broadcast stopped.")

    def _get_player_list_payload(self):
        player_list_for_msg = []
        with self.lock:
            for client_info in self.connected_clients:
                player_list_for_msg.append({
                    "id": client_info["id"], 
                    "name": client_info["name"],
                    "is_ready": client_info.get("is_ready", False) # Include ready status
                })
        return {"players": player_list_for_msg}

    def broadcast_player_list_update(self):
        print("Broadcasting player list update...")
        payload = self._get_player_list_payload()
        with self.lock:
            for client_info in self.connected_clients:
                send_message(client_info["socket"], "player_list_update", payload)

    def _handle_client_thread(self, conn, addr):
        print(f"New client connection from {addr}. Waiting for JOIN_REQUEST...")
        player_id = None
        client_socket = conn

        try:
            join_msg = receive_message(client_socket)
            if join_msg and join_msg.get("type") == "join_request":
                player_name = join_msg.get("payload", {}).get("name", f"Player_{addr[0]}:{addr[1]}")
                
                with self.lock:
                    player_id = self.next_player_id
                    self.next_player_id += 1
                    client_data = {
                        "id": player_id, 
                        "name": player_name, 
                        "socket": client_socket, 
                        "address": addr,
                        "is_ready": False # Add this line
                    }
                    self.connected_clients.append(client_data)
                
                print(f"Player {player_name} (ID: {player_id}) joined from {addr}.")
                
                # Send JOIN_ACKNOWLEDGEMENT
                ack_payload = {
                    "player_id": player_id,
                    "message": f"Welcome {player_name}!",
                    "player_list": self._get_player_list_payload()["players"] # Current player list
                }
                send_message(client_socket, "join_ack", ack_payload)
                
                # Broadcast updated player list to all
                self.broadcast_player_list_update()
            else:
                print(f"Did not receive JOIN_REQUEST from {addr} or malformed. Closing connection.")
                send_message(client_socket, "error", {"message": "JOIN_REQUEST expected."})
                client_socket.close()
                return

            # Loop for other messages
            while self._tcp_server_running: # Check server status as well
                msg = receive_message(client_socket)
                if msg is None: # Connection closed by client or error
                    print(f"Client {player_id} from {addr} disconnected (socket closed/error).")
                    break 
                
                if msg.get("type") == "leave_request":
                    print(f"Received LEAVE_REQUEST from Player ID: {msg.get('payload',{}).get('player_id')}")
                    # Validate if player_id matches this client if necessary
                    break # Exit loop, cleanup will handle removal
                elif msg.get("type") == "set_ready_state":
                    is_ready_payload = msg.get("payload", {}).get("is_ready")
                    if isinstance(is_ready_payload, bool):
                        with self.lock: # Ensure thread-safe update
                            # Find the client in self.connected_clients and update their 'is_ready' status
                            # The 'player_id' for the current client is known in this thread
                            for client_info in self.connected_clients:
                                if client_info["id"] == player_id: # player_id is from the initial join
                                    client_info["is_ready"] = is_ready_payload
                                    print(f"Host: Player {player_id} ({client_info['name']}) set ready state to {is_ready_payload}")
                                    break
                        self.broadcast_player_list_update() # Broadcast the change to all clients
                    else:
                        print(f"Host: Invalid payload for set_ready_state from player {player_id}: {msg.get('payload')}")
                # Add other message type handlers here (e.g., game actions)
                else:
                    print(f"Received unhandled message from {player_id}: {msg}")

        except ConnectionResetError:
            print(f"Client {player_id} from {addr} forcibly closed the connection.")
        except Exception as e:
            print(f"Error handling client {player_id} from {addr}: {e}")
        finally:
            with self.lock:
                client_to_remove = None
                for c in self.connected_clients:
                    if c.get("socket") == client_socket:
                        client_to_remove = c
                        break
                if client_to_remove:
                    self.connected_clients.remove(client_to_remove)
                    print(f"Player {client_to_remove.get('name')} (ID: {client_to_remove.get('id')}) removed.")
                    # Broadcast updated list if a player was successfully registered and then left
                    if player_id is not None: # Ensure they were fully added before broadcasting leave
                         self.broadcast_player_list_update()
            
            if client_socket:
                client_socket.close()
            print(f"Thread for client {addr} (Player ID: {player_id}) terminated.")


    def _run_tcp_server(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.tcp_socket.bind(('0.0.0.0', self.tcp_port))
        except socket.error as e:
            print(f"!!! TCP Server bind failed on port {self.tcp_port}: {e} !!!")
            self._tcp_server_running = False
            return # Critical failure

        self.tcp_socket.listen(5) 
        print(f"TCP Server listening on port {self.tcp_port}...")

        active_client_threads = []
        self._tcp_server_running = True
        while self._tcp_server_running:
            try:
                self.tcp_socket.settimeout(1.0) 
                conn, addr = self.tcp_socket.accept()
                
                client_thread = threading.Thread(target=self._handle_client_thread, args=(conn, addr), daemon=True)
                client_thread.start()
                active_client_threads.append(client_thread)

                # Clean up finished threads (optional, as daemon threads will exit)
                active_client_threads = [t for t in active_client_threads if t.is_alive()]

            except socket.timeout:
                continue 
            except Exception as e:
                if self._tcp_server_running:
                    print(f"TCP Server error: {e}")
                break 
        
        print("TCP Server shutting down client connections...")
        with self.lock:
            for client_info in self.connected_clients:
                client_info["socket"].close()
            self.connected_clients.clear()

        for t in active_client_threads:
            t.join(timeout=1.0) # Attempt to wait for threads to finish

        if self.tcp_socket:
            self.tcp_socket.close()
        print("TCP Server stopped.")

    def start(self):
        if not self._broadcasting:
            self._broadcasting = True
            self._broadcast_thread = threading.Thread(target=self._broadcast_message, daemon=True)
            self._broadcast_thread.start()

        if not self._tcp_server_running:
            self._tcp_server_thread = threading.Thread(target=self._run_tcp_server, daemon=True)
            self._tcp_server_thread.start()
            
    def stop(self):
        print("Stopping host services...")
        self._broadcasting = False # Signal broadcast thread to stop
        self._tcp_server_running = False # Signal TCP server thread to stop

        if self._broadcast_thread and self._broadcast_thread.is_alive():
            # UDP socket is closed in its thread, no explicit join needed as it's daemon
            # and sleep/sendto will eventually unblock or error out.
            pass
        
        if self._tcp_server_thread and self._tcp_server_thread.is_alive():
            self._tcp_server_thread.join(timeout=2) # Wait for TCP server thread

        print("Host services stopped.")

if __name__ == '__main__':
    host = GameHost(host_name="MainTestHost", tcp_port=5555)
    host.start()
    
    print("Host started. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
            # You can add commands here to interact with the host, e.g., print player list
            # with host.lock:
            #    if host.connected_clients:
            #        print(f"Connected players: {[(p['id'], p['name']) for p in host.connected_clients]}")
    except KeyboardInterrupt:
        print("\nShutting down host from main...")
    finally:
        host.stop()
        print("Host shut down complete.")
