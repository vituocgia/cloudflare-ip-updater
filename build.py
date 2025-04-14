import os
import subprocess
import sys
import shutil

def check_dependencies():
    """
    Check and install required build dependencies
    """
    try:
        import PyInstaller
        import PyQt5
        import requests
        import cryptography
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Installing required dependencies...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 
            'pyinstaller', 'PyQt5', 'requests', 'cryptography'])
        print("Dependencies installed successfully.")

def create_icon():
    """
    Create a default icon if not exists
    """
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
    
    # Check if icon already exists
    if not os.path.exists(icon_path):
        print("Creating default icon...")
        try:
            # For a simple solution, copy from a resource directory if it exists
            resource_icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'icon.ico')
            if os.path.exists(resource_icon):
                shutil.copy(resource_icon, icon_path)
                print(f"Icon copied from resources to {icon_path}")
            else:
                # Option 2: For this example, we'll download a simple icon
                # In production, you might want to embed a default icon
                import requests
                print("Downloading a placeholder icon...")
                response = requests.get('https://www.cloudflare.com/favicon.ico')
                with open(icon_path, 'wb') as f:
                    f.write(response.content)
                print(f"Created default icon at {icon_path}")
        except Exception as e:
            print(f"Warning: Could not create icon: {e}")
            print("Application will run without an icon.")
    else:
        print(f"Icon already exists at {icon_path}")

def clean_build_dir():
    """
    Clean up previous build directories
    """
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            print(f"Cleaning {dir_name} directory...")
            try:
                shutil.rmtree(dir_name)
                print(f"Removed {dir_name} directory")
            except Exception as e:
                print(f"Error cleaning {dir_name}: {e}")

def build_executable():
    """
    Build the executable using PyInstaller
    """
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Clean previous build
    clean_build_dir()

    # Create build command
    build_command = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=CloudflareIPUpdater',
        '--add-data', f'icon.ico{os.pathsep}.',
        '--icon=icon.ico',
        'main.py'
    ]

    try:
        print("Starting build process...")
        # Run PyInstaller
        result = subprocess.run(build_command, capture_output=True, text=True)
        
        # Check build output
        if result.returncode == 0:
            print("Build successful!")
            print("Executable created at: dist/CloudflareIPUpdater.exe")
            
            # Copy config file template to dist folder
            if not os.path.exists('dist/updater_config.json'):
                with open('dist/updater_config.json', 'w') as f:
                    f.write('[]')
                print("Created empty configuration file")
                
            print("\nInstallation Instructions:")
            print("1. Copy CloudflareIPUpdater.exe from the 'dist' folder to your desired location")
            print("2. Run the application to set up your domains")
        else:
            print("Build failed.")
            print("Error output:", result.stderr)
    
    except Exception as e:
        print(f"Build error: {e}")

def main():
    print("===== Cloudflare IP Updater Build Script =====")
    
    # Check and install dependencies
    print("\nChecking dependencies...")
    check_dependencies()

    # Create icon if needed
    print("\nChecking icon...")
    create_icon()

    # Build executable
    print("\nBuilding executable...")
    build_executable()
    
    print("\nBuild process complete.")

if __name__ == '__main__':
    main()