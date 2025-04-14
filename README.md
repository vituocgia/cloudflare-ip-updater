# Cloudflare Dynamic IP Updater

## Overview
A lightweight, user-friendly desktop application that automatically updates your Cloudflare DNS records with your current dynamic IP address.

## Features
- **Automatic IP Monitoring**: Detects IP changes and updates DNS records automatically
- **Multiple Domain Support**: Manage multiple domains and DNS records 
- **Configurable Update Intervals**: Set different check frequencies for each domain
- **Secure Credential Storage**: Encrypts and safely stores your Cloudflare API tokens
- **User-Friendly Interface**: Clean, intuitive GUI with visual status indicators
- **Domain Management**: Add, edit, and remove domains through the interface
- **Manual Update Option**: Force immediate update of all domains
- **Detailed Logging**: View real-time logs of all activity
- **System Tray Integration**: Run in the background with minimal interference
- **Windows Startup Option**: Launch automatically when Windows starts
- **Stable Configuration**: Maintains settings between application restarts

## Prerequisites
- Windows 10/11
- Internet connection
- Cloudflare account with API access

## Getting Started

### Obtaining Cloudflare Credentials
1. Log in to your Cloudflare dashboard at https://dash.cloudflare.com
2. Select your domain
3. Go to "Overview" and note your Zone ID (found in the right sidebar)
4. Go to "My Profile" → "API Tokens"
5. Create a new token with:
   - Zone.DNS:Edit permissions
   - Include specific zone resources (your domain)
   - Save the token - you'll need it to configure the application

### Installation Options

#### Option 1: Download Pre-built Executable
1. Download the latest release from the releases page
2. Extract the ZIP file to your preferred location
3. Run `CloudflareIPUpdater.exe`

#### Option 2: Build from Source
1. Clone the repository
2. Set up a virtual environment (recommended):
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Run the build script:
   ```
   python build.py
   ```
5. Find the executable in the `dist/` folder

### Building from Source (Detailed)
```
# Clone the repository
git clone https://github.com/yourusername/cloudflare-ip-updater.git
cd cloudflare-ip-updater

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run build script to create executable
python build.py
```

## Usage

### Adding Domains
1. Launch the application
2. Click "Add Domain" button in the toolbar or main interface
3. Fill in your Cloudflare credentials:
   - Domain Name: The full domain name to update (e.g., `subdomain.example.com`)
   - Zone ID: Your domain's Zone ID from Cloudflare
   - API Token: Your Cloudflare API token
   - Update Interval: How frequently to check for IP changes (in minutes)
4. Click "Test Connection" to verify your credentials
5. Click "Save" to add the domain

### Managing Domains
- **Start/Stop Updates**: Click the "Start" or "Stop" button for a specific domain
- **Edit Domain**: Update domain settings with the "Edit" button
- **Remove Domain**: Delete domains you no longer need with the "Remove" button
- **Start/Stop All**: Control all domains at once with the "Start All" or "Stop All" buttons
- **Manual Update**: Force an immediate update of all domains with "Manual Update"

### Application Settings
- **Windows Startup**: Enable or disable automatic startup with Windows using the checkbox in the status bar
- **System Tray**: Minimize to the system tray by closing the window
- **Current IP**: View your current public IP in the status bar

### Event Log
- View real-time logs of all IP check and update activities
- Clear the log with the "Clear Log" button
- More detailed logs are saved to `ip_updater.log` file

## Troubleshooting

### Common Issues
- **API Token Errors**: Verify your token has the correct permissions (Zone.DNS:Edit)
- **Zone ID Errors**: Double-check your Zone ID matches the domain
- **Domain Not Found**: Ensure the domain record exists in your Cloudflare DNS settings
- **Update Failures**: Check your internet connection and firewall settings
- **Configuration Issues**: If settings don't persist, check file permissions in the application directory

### Logging
The application creates a log file (`ip_updater.log`) in its directory with detailed information about operations and errors.

## Recent Improvements
- Enhanced configuration persistence with robust encryption
- Improved IP updating with multiple fallback services
- Complete domain management capabilities (add/edit/remove)
- More reliable connection testing
- Detailed activity logging
- Better error handling and recovery
- Enhanced visual status indicators
- Current IP display in status bar
- More intuitive user interface

## Security Notes
- API tokens and credentials are encrypted before being stored locally
- The application only requires permissions to modify DNS records
- All communication uses HTTPS with Cloudflare's API

## License
[MIT License](LICENSE)

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request