import os
import json
import base64
import winreg
import sys
import shutil
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class ConfigManager:
    def __init__(self, config_file=None):
        """
        Initialize ConfigManager with optional config file path
        """
        if config_file is None:
            # For bundled executable, use the directory where the exe is located
            if getattr(sys, 'frozen', False):
                # PyInstaller creates a temp folder and stores path in _MEIPASS,
                # but we want to store config next to the executable
                exe_dir = os.path.dirname(sys.executable)
                self.config_file = os.path.join(exe_dir, 'updater_config.json')
            else:
                # For development, use the script directory
                app_dir = os.path.dirname(os.path.abspath(__file__))
                self.config_file = os.path.join(app_dir, 'updater_config.json')
        else:
            self.config_file = config_file
            
        print(f"Using config file: {self.config_file}")
        self._encryption_key = self._generate_key()
        
        try:
            # Ensure config file directory exists
            config_dir = os.path.dirname(os.path.abspath(self.config_file))
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            # Ensure config file exists with valid JSON
            if not os.path.exists(self.config_file):
                with open(self.config_file, 'w') as f:
                    f.write('[]')
                print(f"Created new empty config file: {self.config_file}")
            else:
                # Try to migrate config if needed
                try:
                    self._try_migrate_config()
                except Exception as e:
                    print(f"Migration error (non-critical): {e}")
        except Exception as e:
            print(f"Config initialization error: {e}")
            # Create fallback config if possible
            try:
                with open(self.config_file, 'w') as f:
                    f.write('[]')
            except:
                pass

    def _generate_key(self):
        """
        Generate a stable encryption key based on system-specific information
        """
        try:
            # Need a stable key that doesn't change between sessions
            # We'll use system-specific but consistent information
            
            # Create a stable salt - use computer name and user name
            machine_id = os.environ.get('COMPUTERNAME', '')
            user_id = os.environ.get('USERNAME', '')
            
            if not machine_id:
                # Fallback for non-Windows systems
                try:
                    import socket
                    machine_id = socket.gethostname()
                except:
                    machine_id = "unknown"
            
            # Create a stable salt
            salt_string = f"CloudflareUpdater:{machine_id}:{user_id}"
            salt = salt_string.encode()
            
            # Create key derivation function
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000
            )
            
            # Create encryption key from system information
            base_key = f"{machine_id}:{user_id}:CloudflareUpdaterKey"
            key = base64.urlsafe_b64encode(kdf.derive(base_key.encode()))
            
            return key
        except Exception as e:
            print(f"Warning: Error generating encryption key: {e}")
            # Fallback to a fixed key if we can't generate a proper one
            # Note: Less secure but better than losing data
            return base64.urlsafe_b64encode(b"CloudflareIPUpdaterDefaultKey123456789012")

    def _try_migrate_config(self):
        """
        Attempt to migrate encrypted config from older versions
        """
        try:
            if not os.path.exists(self.config_file):
                return False
                
            with open(self.config_file, 'r') as f:
                try:
                    domains = json.load(f)
                    if not isinstance(domains, list) or not domains:
                        return False
                except:
                    return False
                    
            # Check if we need to migrate (try decrypting first token)
            if domains and isinstance(domains[0], dict) and 'api_token' in domains[0]:
                try:
                    self._decrypt_value(domains[0]['api_token'])
                    # If no exception, decryption worked with current key, no migration needed
                    return False
                except:
                    # Decryption failed, try alternative keys
                    print("Attempting config migration...")
                    
                    # List of possible key generation methods (from older versions)
                    alt_keys = self._get_alternative_keys()
                    
                    # Try each alternative key
                    for key_name, alt_key in alt_keys.items():
                        try:
                            migrated = False
                            for domain in domains:
                                if 'api_token' in domain and domain['api_token']:
                                    # Try decrypting with alternative key
                                    try:
                                        f = Fernet(alt_key)
                                        decrypted = f.decrypt(domain['api_token'].encode()).decode()
                                        
                                        # If successful, re-encrypt with new key
                                        domain['api_token'] = self._encrypt_value(decrypted)
                                        migrated = True
                                    except:
                                        continue
                            
                            if migrated:
                                print(f"Successfully migrated config using {key_name} key")
                                # Save migrated config
                                with open(self.config_file, 'w') as f:
                                    json.dump(domains, f, indent=4)
                                return True
                        except:
                            continue
                            
                    print("Config migration failed - could not decrypt with any known key")
                    return False
            
            return False
        except Exception as e:
            print(f"Error during config migration: {e}")
            return False

    def _get_alternative_keys(self):
        """
        Generate alternative encryption keys that might have been used in previous versions
        """
        keys = {}
        
        try:
            # Try different variants of keys that might have been used
            
            # 1. Process ID based key (original method)
            salt1 = os.urandom(16)
            kdf1 = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt1,
                iterations=100000
            )
            keys["process_id"] = base64.urlsafe_b64encode(kdf1.derive(
                str(os.getpid()).encode() + 
                str(os.getlogin()).encode()
            ))
            
            # 2. Machine name based
            machine_id = os.environ.get('COMPUTERNAME', '')
            if not machine_id:
                try:
                    import socket
                    machine_id = socket.gethostname()
                except:
                    machine_id = "unknown"
            
            salt2 = b"CloudflareUpdater"
            kdf2 = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt2,
                iterations=100000
            )
            keys["machine_id"] = base64.urlsafe_b64encode(kdf2.derive(machine_id.encode()))
            
            # 3. Default fallback key
            keys["default"] = base64.urlsafe_b64encode(b"CloudflareIPUpdaterDefaultKey123456789012")
            
        except Exception as e:
            print(f"Error generating alternative keys: {e}")
        
        return keys

    def _encrypt_value(self, value):
        """
        Encrypt a sensitive value
        """
        if not value:
            return ''
        
        f = Fernet(self._encryption_key)
        return f.encrypt(value.encode()).decode()

    def _decrypt_value(self, encrypted_value):
        """
        Decrypt a sensitive value
        """
        if not encrypted_value:
            return ''
        
        f = Fernet(self._encryption_key)
        return f.decrypt(encrypted_value.encode()).decode()

    def is_startup_enabled(self):
        """
        Check if application is set to run at Windows startup
        """
        try:
            key_path = r'Software\Microsoft\Windows\CurrentVersion\Run'
            key_name = 'CloudflareIPUpdater'
            
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            try:
                winreg.QueryValueEx(key, key_name)
                winreg.CloseKey(key)
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            print(f"Error checking startup status: {e}")
            return False

    def save_config(self, domains):
        """
        Save multiple domain configurations
        
        :param domains: List of domain dictionaries
        """
        # Create a safe copy and encrypt sensitive fields
        safe_domains = []
        for domain in domains:
            if domain and isinstance(domain, dict):  # Validate domain is not None and is a dict
                safe_domain = domain.copy()
                
                # Ensure required keys exist
                required_keys = ['api_token', 'zone_id', 'domain', 'interval']
                for key in required_keys:
                    if key not in safe_domain:
                        if key == 'interval':
                            safe_domain[key] = 15  # Default interval
                        else:
                            safe_domain[key] = ''
                
                # Encrypt sensitive fields
                if 'api_token' in safe_domain and safe_domain['api_token']:
                    safe_domain['api_token'] = self._encrypt_value(safe_domain['api_token'])
                
                safe_domains.append(safe_domain)

        try:
            # Create backup of existing config
            if os.path.exists(self.config_file):
                backup_file = f"{self.config_file}.bak"
                shutil.copy2(self.config_file, backup_file)
                
            # Write new config
            with open(self.config_file, 'w') as f:
                json.dump(safe_domains, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            # Try to restore from backup if save failed
            try:
                if os.path.exists(f"{self.config_file}.bak"):
                    shutil.copy2(f"{self.config_file}.bak", self.config_file)
            except:
                pass
            return False

    def load_config(self):
        """
        Load domain configurations, decrypting sensitive fields
        
        :return: List of domain configurations
        """
        try:
            # If config file doesn't exist, create it with empty array
            if not os.path.exists(self.config_file):
                with open(self.config_file, 'w') as f:
                    f.write('[]')
                return []

            with open(self.config_file, 'r') as f:
                try:
                    domains = json.load(f)
                    if not isinstance(domains, list):
                        print("Warning: Config file content is not a list. Resetting.")
                        domains = []
                except json.JSONDecodeError:
                    print("Warning: Invalid JSON in config file. Resetting.")
                    domains = []

            # Decrypt sensitive fields
            safe_domains = []
            for domain in domains:
                if domain and isinstance(domain, dict):  # Validate domain
                    safe_domain = domain.copy()
                    
                    # Decrypt API token if exists
                    if 'api_token' in safe_domain and safe_domain['api_token']:
                        try:
                            safe_domain['api_token'] = self._decrypt_value(safe_domain['api_token'])
                        except Exception as e:
                            print(f"Warning: Could not decrypt API token: {e}")
                            # Keep encrypted value if decryption fails
                    
                    safe_domains.append(safe_domain)

            return safe_domains
        except Exception as e:
            print(f"Error loading config: {e}")
            return []

    def clear_config(self):
        """
        Clear saved configuration
        """
        try:
            if os.path.exists(self.config_file):
                # Create backup before clearing
                backup_file = f"{self.config_file}.bak"
                shutil.copy2(self.config_file, backup_file)
                
                # Write empty array to config file
                with open(self.config_file, 'w') as f:
                    f.write('[]')
                return True
        except Exception as e:
            print(f"Error clearing config: {e}")
            return False

    def set_windows_startup(self, enable=True):
        """
        Add or remove application from Windows startup
        
        :param enable: True to add to startup, False to remove
        """
        try:
            # Get path to executable
            if getattr(sys, 'frozen', False):
                # PyInstaller creates a temp folder and stores path in _MEIPASS
                app_path = sys.executable
            else:
                app_path = os.path.abspath(sys.argv[0])

            # Registry key for Windows startup
            key_path = r'Software\Microsoft\Windows\CurrentVersion\Run'
            key_name = 'CloudflareIPUpdater'

            # Open registry key
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            except FileNotFoundError:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)

            if enable:
                # Add to startup
                winreg.SetValueEx(key, key_name, 0, winreg.REG_SZ, f'"{app_path}"')
                print("Added to Windows startup")
            else:
                # Remove from startup
                try:
                    winreg.DeleteValue(key, key_name)
                    print("Removed from Windows startup")
                except FileNotFoundError:
                    pass  # Value already doesn't exist

            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error setting Windows startup: {e}")
            return False