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

def create_version_info():
    """
    Create version info file for the executable
    """
    version_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'version_info.txt')
    
    if not os.path.exists(version_path):
        print("Creating version info file...")
        version_content = """# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x40004,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'XoneVN'),
        StringStruct(u'FileDescription', u'Updates Cloudflare DNS with your current IP address'),
        StringStruct(u'FileVersion', u'0.1.0'),
        StringStruct(u'InternalName', u'cloudflare_ip_updater'),
        StringStruct(u'LegalCopyright', u'Copyright (c) 2025 XoneVN'),
        StringStruct(u'OriginalFilename', u'CloudflareIPUpdater.exe'),
        StringStruct(u'ProductName', u'Cloudflare Dynamic IP Updater'),
        StringStruct(u'ProductVersion', u'0.1.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
        
        with open(version_path, 'w') as f:
            f.write(version_content)
        print(f"Created version info file at {version_path}")
    else:
        print("Version info file already exists")

def build_executable():
    """
    Build the executable using PyInstaller
    """
    # Ensure we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Clean previous build
    clean_build_dir()
    
    # Create version info file
    create_version_info()

    # Create build command
    build_command = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=CloudflareIPUpdater',
        '--add-data', f'icon.ico{os.pathsep}.',
        '--icon=icon.ico',
        '--version-file=version_info.txt',
        'src/main.py'
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