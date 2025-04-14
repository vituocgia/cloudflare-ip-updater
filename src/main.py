import sys
import os
import logging
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox, 
    QSystemTrayIcon, QMenu, QCheckBox, QTableWidget, QTableWidgetItem, 
    QDialog, QFormLayout, QHeaderView, QAbstractItemView, QSpinBox,
    QGroupBox, QSplitter, QAction, QToolBar, QStatusBar, QComboBox
)
from PyQt5.QtGui import QIcon, QPixmap, QColor, QFont
from PyQt5.QtCore import Qt, QTimer, QSize

import threading

from ip_updater import CloudflareIPUpdater
from config_manager import ConfigManager

class DomainDialog(QDialog):
    def __init__(self, parent=None, domain_data=None):
        super().__init__(parent)
        self.setWindowTitle('Domain Configuration')
        self.setModal(True)
        self.domain_data = domain_data
        self.setMinimumWidth(450)
        self.init_ui()
        
        # If editing existing domain, populate fields
        if domain_data:
            self.setWindowTitle('Edit Domain')
            self.populate_fields(domain_data)

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Form layout for inputs
        form_layout = QFormLayout()
        
        # Domain Name Input
        self.domain_input = QLineEdit()
        self.domain_input.setPlaceholderText('e.g., example.com or subdomain.example.com')
        form_layout.addRow('Domain Name:', self.domain_input)
        
        # Zone ID Input
        self.zone_id_input = QLineEdit()
        self.zone_id_input.setPlaceholderText('Your Cloudflare Zone ID')
        form_layout.addRow('Cloudflare Zone ID:', self.zone_id_input)
        
        # API Token Input
        self.api_token_input = QLineEdit()
        self.api_token_input.setEchoMode(QLineEdit.Password)
        self.api_token_input.setPlaceholderText('Your Cloudflare API Token')
        form_layout.addRow('Cloudflare API Token:', self.api_token_input)
        
        # Show/Hide password
        self.show_token_checkbox = QCheckBox("Show Token")
        self.show_token_checkbox.stateChanged.connect(self.toggle_token_visibility)
        form_layout.addRow('', self.show_token_checkbox)
        
        # Interval Input
        self.interval_input = QSpinBox()
        self.interval_input.setRange(1, 1440)  # 1 minute to 24 hours
        self.interval_input.setValue(15)
        self.interval_input.setSuffix(" minutes")
        form_layout.addRow('Update Interval:', self.interval_input)
        
        # Add form to layout
        layout.addLayout(form_layout)
        
        # Add test connection button
        test_btn = QPushButton('Test Connection')
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_button = QPushButton('Save')
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton('Cancel')
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
    
    def toggle_token_visibility(self, state):
        if state == Qt.Checked:
            self.api_token_input.setEchoMode(QLineEdit.Normal)
        else:
            self.api_token_input.setEchoMode(QLineEdit.Password)
    
    def populate_fields(self, domain_data):
        """Populate fields with existing domain data"""
        self.domain_input.setText(domain_data.get('domain', ''))
        self.zone_id_input.setText(domain_data.get('zone_id', ''))
        self.api_token_input.setText(domain_data.get('api_token', ''))
        self.interval_input.setValue(domain_data.get('interval', 15))
    
    def test_connection(self):
        """Test connection to Cloudflare API"""
        domain = self.domain_input.text().strip()
        zone_id = self.zone_id_input.text().strip()
        api_token = self.api_token_input.text().strip()
        
        if not all([domain, zone_id, api_token]):
            QMessageBox.warning(self, 'Incomplete Information', 
                                'Please fill in all fields to test connection.')
            return
        
        # Create temporary updater just for testing
        ip_updater = CloudflareIPUpdater()
        
        try:
            # Show "testing" message
            QApplication.setOverrideCursor(Qt.WaitCursor)
            success, message = ip_updater.test_connection(api_token, zone_id, domain)
            QApplication.restoreOverrideCursor()
            
            if success:
                QMessageBox.information(self, 'Connection Successful', message)
            else:
                QMessageBox.warning(self, 'Connection Failed', message)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, 'Error', f'Error testing connection: {str(e)}')

    def get_domain_data(self):
        return {
            'domain': self.domain_input.text().strip(),
            'zone_id': self.zone_id_input.text().strip(),
            'api_token': self.api_token_input.text().strip(),
            'interval': self.interval_input.value()
        }

class MainApplication(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.ip_updater = CloudflareIPUpdater()
        self.domains = []
        self.running_domains = {}
        
        # IMPORTANT: Initialize logger first before any other methods that might use it
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        # Then initialize UI and other components
        self.init_ui()
        self.setup_tray_icon()
        self.load_saved_domains()
        
        # Set up auto-save timer (every 5 minutes)
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.save_domains)
        self.auto_save_timer.start(5 * 60 * 1000)  # 5 minutes in milliseconds

    def init_ui(self):
        self.setWindowTitle('Cloudflare Dynamic IP Updater')
        self.setGeometry(100, 100, 900, 650)
        
        # Set window icon if available
        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Add toolbar actions
        add_action = QAction("Add Domain", self)
        add_action.triggered.connect(self.add_domain)
        toolbar.addAction(add_action)
        
        start_all_action = QAction("Start All", self)
        start_all_action.triggered.connect(self.start_all_domains)
        toolbar.addAction(start_all_action)
        
        stop_all_action = QAction("Stop All", self)
        stop_all_action.triggered.connect(self.stop_all_domains)
        toolbar.addAction(stop_all_action)
        
        update_all_action = QAction("Update All", self)
        update_all_action.triggered.connect(self.manual_update_all_domains)
        toolbar.addAction(update_all_action)
        
        toolbar.addSeparator()
        
        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(settings_action)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Split view between domains table and log
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        # Upper part - Domains list
        domains_container = QWidget()
        domains_layout = QVBoxLayout()
        domains_container.setLayout(domains_layout)
        
        # Domains Header
        domains_header = QLabel("Managed Domains")
        domains_header.setStyleSheet("font-size: 16px; font-weight: bold;")
        domains_layout.addWidget(domains_header)

        # Domains Table
        self.domains_table = QTableWidget()
        self.domains_table.setColumnCount(6)
        self.domains_table.setHorizontalHeaderLabels(['Domain', 'Zone ID', 'Interval', 'Status', 'Last Update', 'Actions'])
        self.domains_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.domains_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.domains_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)  # Domain column stretches
        self.domains_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Actions column resizes to content
        
        domains_layout.addWidget(self.domains_table)
        
        # Domain control buttons layout
        domain_buttons_layout = QHBoxLayout()
        
        # Add Domain Button
        add_domain_btn = QPushButton('Add Domain')
        add_domain_btn.clicked.connect(self.add_domain)
        domain_buttons_layout.addWidget(add_domain_btn)
        
        # Start/Stop All Buttons
        self.start_all_btn = QPushButton('Start All')
        self.start_all_btn.clicked.connect(self.start_all_domains)
        domain_buttons_layout.addWidget(self.start_all_btn)
        
        self.stop_all_btn = QPushButton('Stop All')
        self.stop_all_btn.clicked.connect(self.stop_all_domains)
        domain_buttons_layout.addWidget(self.stop_all_btn)
        
        # Manual Update Button
        manual_update_btn = QPushButton('Manual Update')
        manual_update_btn.clicked.connect(self.manual_update_all_domains)
        domain_buttons_layout.addWidget(manual_update_btn)
        
        # Right-align the buttons
        domain_buttons_layout.addStretch(1)
        
        domains_layout.addLayout(domain_buttons_layout)
        splitter.addWidget(domains_container)
        
        # Lower part - Log display
        log_container = QWidget()
        log_layout = QVBoxLayout()
        log_container.setLayout(log_layout)
        
        # Log Header with control buttons
        log_header_layout = QHBoxLayout()
        
        log_label = QLabel('Event Log')
        log_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        log_header_layout.addWidget(log_label)
        
        # Add log controls (right-aligned)
        log_header_layout.addStretch(1)
        
        clear_log_btn = QPushButton('Clear Log')
        clear_log_btn.clicked.connect(self.clear_log)
        log_header_layout.addWidget(clear_log_btn)
        
        log_layout.addLayout(log_header_layout)
        
        # Log Display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        
        splitter.addWidget(log_container)
        
        # Set initial sizes for the splitter (2/3 for domains, 1/3 for log)
        splitter.setSizes([400, 200])
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Create the checkbox first, then add it to the status bar
        self.startup_checkbox = QCheckBox('Start with Windows')
        self.startup_checkbox.stateChanged.connect(self.toggle_windows_startup)
        self.status_bar.addPermanentWidget(self.startup_checkbox)

        # Check if already set to start with Windows
        try:
            self.startup_checkbox.setChecked(self.config_manager.is_startup_enabled())
        except Exception as e:
            self.update_log_display(f"Error checking startup status: {str(e)}")
            self.startup_checkbox.setChecked(False)
        
        # Current IP display in status bar
        self.current_ip_label = QLabel("Current IP: Checking...")
        self.status_bar.addWidget(self.current_ip_label)
        
        # Start IP update check
        self.update_current_ip_display()
        
        # Set up timer to update IP display every 5 minutes
        self.ip_display_timer = QTimer(self)
        self.ip_display_timer.timeout.connect(self.update_current_ip_display)
        self.ip_display_timer.start(5 * 60 * 1000)  # 5 minutes

    def update_current_ip_display(self):
        """Update the current IP display in the status bar"""
        def update_label():
            current_ip = self.ip_updater.get_current_ip()
            if current_ip:
                self.current_ip_label.setText(f"Current IP: {current_ip}")
            else:
                self.current_ip_label.setText("Current IP: Unable to detect")
        
        # Run in another thread to avoid UI freezing
        threading.Thread(target=update_label, daemon=True).start()

    def show_settings(self):
        """Show application settings dialog"""
        # A simple example for now - you can expand this
        msg = QMessageBox(self)
        msg.setWindowTitle("Settings")
        msg.setText("Settings functionality will be implemented in a future version.")
        msg.setInformativeText("Currently, you can configure startup with Windows using the checkbox in the status bar.")
        msg.setIcon(QMessageBox.Information)
        msg.exec_()

    def clear_log(self):
        """Clear the log display"""
        reply = QMessageBox.question(self, 'Clear Log', 
                                     'Are you sure you want to clear the log?',
                                     QMessageBox.Yes | QMessageBox.No, 
                                     QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.log_display.clear()
            self.update_log_display("Log cleared")

    def setup_logging(self):
        """Configure logging with proper path handling"""
        try:
            # For bundled executable, use the directory where the exe is located
            if getattr(sys, 'frozen', False):
                log_dir = os.path.dirname(sys.executable)
            else:
                # For development, use the script directory
                log_dir = os.path.dirname(os.path.abspath(__file__))
                
            log_file = os.path.join(log_dir, 'ip_updater.log')
            
            # If can't write to that directory, fall back to user's home directory
            if not os.access(log_dir, os.W_OK):
                home_dir = os.path.expanduser("~")
                log_file = os.path.join(home_dir, 'ip_updater.log')
                print(f"Using alternative log file location: {log_file}")
            
            # Configure logging
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file),
                    logging.StreamHandler()
                ]
            )
            
            # Add initial log
            self.update_log_display(f"Application started at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.update_log_display(f"Log file: {log_file}")
            self.update_log_display(f"Config file: {self.config_manager.config_file}")
            
        except Exception as e:
            # Fallback to console-only logging if file logging fails
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.StreamHandler()
                ]
            )
            self.update_log_display(f"Warning: Could not set up file logging: {e}")

    def setup_tray_icon(self):
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon(self)
        
        # Get icon path and set icon if available
        icon_path = self.get_icon_path()
        if icon_path and os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            # Use a default icon from Qt resources if available
            self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        
        # Create tray menu
        tray_menu = QMenu()
        
        # Show action
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show_and_raise)
        
        # Manual update action
        update_action = tray_menu.addAction("Manual Update")
        update_action.triggered.connect(self.manual_update_all_domains)
        
        tray_menu.addSeparator()
        
        # Exit action
        exit_action = tray_menu.addAction("Exit")
        exit_action.triggered.connect(self.close_application)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.setToolTip('Cloudflare IP Updater')
        
        # Connect the activated signal
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def get_icon_path(self):
        """Get the correct path for the icon file"""
        try:
            # For bundled executable, use PyInstaller's resource path
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, 'icon.ico')
                if os.path.exists(icon_path):
                    return icon_path
            
            # Check relative to the current script directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            icon_paths = [
                os.path.join(script_dir, 'icon.ico'),
                os.path.join(script_dir, '..', 'icon.ico'),
                os.path.join(os.getcwd(), 'icon.ico')
            ]
            
            for path in icon_paths:
                if os.path.exists(path):
                    return path
                    
            print("Warning: Icon file not found, using default icon")
            return None
        except Exception as e:
            print(f"Error locating icon: {e}")
            return None

    def load_saved_domains(self):
        """
        Load saved domains from configuration
        """
        saved_domains = self.config_manager.load_config()
        
        # Clear existing rows
        self.domains_table.setRowCount(0)
        self.domains = []

        # Populate table with saved domains
        for domain_config in saved_domains:
            self.add_domain_to_table(domain_config)
        
        self.update_log_display(f"Loaded {len(saved_domains)} domains from configuration")

    def add_domain(self):
        """
        Open dialog to add a new domain
        """
        dialog = DomainDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            domain_data = dialog.get_domain_data()
            
            # Validate inputs
            if not all([domain_data['api_token'], domain_data['zone_id'], domain_data['domain']]):
                QMessageBox.warning(self, 'Error', 'Please fill in all fields')
                return

            # Add domain to table and configurations
            self.add_domain_to_table(domain_data)
            
            # Save updated configurations
            self.save_domains()
            
            # Log the addition
            self.update_log_display(f"Added domain: {domain_data['domain']}")

    def edit_domain(self, row):
        """
        Open dialog to edit an existing domain
        """
        if row < 0 or row >= len(self.domains):
            return
            
        # Get existing domain data
        domain_data = self.domains[row]
        
        # Open edit dialog with current data
        dialog = DomainDialog(self, domain_data)
        if dialog.exec_() == QDialog.Accepted:
            # Get updated data
            updated_data = dialog.get_domain_data()
            
            # Validate inputs
            if not all([updated_data['api_token'], updated_data['zone_id'], updated_data['domain']]):
                QMessageBox.warning(self, 'Error', 'Please fill in all fields')
                return
            
            # Stop updating if running
            domain_key = f"{domain_data['domain']}_{domain_data['zone_id']}"
            was_running = domain_key in self.running_domains and self.running_domains[domain_key]
            
            if was_running:
                self.ip_updater.stop_updating(domain_data['domain'], domain_data['zone_id'])
            
            # Update domain in list
            self.domains[row] = updated_data
            
            # Update table
            self.update_domain_in_table(row, updated_data)
            
            # Restart if it was running
            if was_running:
                self.start_domain_update(row)
            
            # Save updated configurations
            self.save_domains()
            
            # Log the edit
            self.update_log_display(f"Updated domain: {updated_data['domain']}")

    def remove_domain(self, row):
        """
        Remove a domain from the configuration
        """
        if row < 0 or row >= len(self.domains):
            return
            
        domain = self.domains[row]['domain']
        zone_id = self.domains[row]['zone_id']
        
        # Confirm deletion
        reply = QMessageBox.question(
            self, 'Confirm Removal', 
            f'Are you sure you want to remove {domain}?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Stop updating if running
            self.ip_updater.stop_updating(domain, zone_id)
            
            # Remove from running_domains tracking
            domain_key = f"{domain}_{zone_id}"
            if domain_key in self.running_domains:
                del self.running_domains[domain_key]
            
            # Remove from domains list
            self.domains.pop(row)
            
            # Remove from table
            self.domains_table.removeRow(row)
            
            # Save updated configurations
            self.save_domains()
            
            # Log the removal
            self.update_log_display(f"Removed domain: {domain}")

    def add_domain_to_table(self, domain_data):
        """
        Add a domain to the table and domains list
        """
        row = self.domains_table.rowCount()
        self.domains_table.insertRow(row)

        # Domain name
        self.domains_table.setItem(row, 0, QTableWidgetItem(domain_data['domain']))
        
        # Zone ID (shortened for display)
        zone_id = domain_data['zone_id']
        if len(zone_id) > 10:
            display_zone_id = zone_id[:7] + '...'
        else:
            display_zone_id = zone_id
        zone_item = QTableWidgetItem(display_zone_id)
        zone_item.setToolTip(zone_id)  # Show full zone ID on hover
        self.domains_table.setItem(row, 1, zone_item)
        
        # Interval
        self.domains_table.setItem(row, 2, QTableWidgetItem(f"{domain_data.get('interval', 15)} min"))
        
        # Status
        status_item = QTableWidgetItem('Stopped')
        status_item.setForeground(QColor(255, 0, 0))  # Red for stopped
        self.domains_table.setItem(row, 3, status_item)
        
        # Last Update
        self.domains_table.setItem(row, 4, QTableWidgetItem("Never"))
        
        # Actions - Add buttons
        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(2, 2, 2, 2)
        actions_layout.setSpacing(2)
        
        # Start/Stop button
        start_stop_btn = QPushButton('Start')
        start_stop_btn.setFixedSize(60, 28)
        start_stop_btn.clicked.connect(lambda: self.toggle_domain_update(row))
        actions_layout.addWidget(start_stop_btn)
        
        # Edit button
        edit_btn = QPushButton('Edit')
        edit_btn.setFixedSize(60, 28)
        edit_btn.clicked.connect(lambda: self.edit_domain(row))
        actions_layout.addWidget(edit_btn)
        
        # Remove button
        remove_btn = QPushButton('Remove')
        remove_btn.setFixedSize(60, 28)
        remove_btn.clicked.connect(lambda: self.remove_domain(row))
        actions_layout.addWidget(remove_btn)
        
        actions_widget.setLayout(actions_layout)
        self.domains_table.setCellWidget(row, 5, actions_widget)

        # Store full domain data and adjust row height
        self.domains.append(domain_data)
        self.domains_table.setRowHeight(row, 40)

    def update_domain_in_table(self, row, domain_data):
        """
        Update domain information in the table
        """
        if row < 0 or row >= self.domains_table.rowCount():
            return
            
        # Update domain name
        self.domains_table.item(row, 0).setText(domain_data['domain'])
        
        # Update Zone ID (shortened for display)
        zone_id = domain_data['zone_id']
        if len(zone_id) > 10:
            display_zone_id = zone_id[:7] + '...'
        else:
            display_zone_id = zone_id
        self.domains_table.item(row, 1).setText(display_zone_id)
        self.domains_table.item(row, 1).setToolTip(zone_id)
        
        # Update interval
        self.domains_table.item(row, 2).setText(f"{domain_data.get('interval', 15)} min")

    def toggle_domain_update(self, row):
        """
        Start or stop update for a specific domain
        """
        if row < 0 or row >= len(self.domains):
            return
            
        domain_data = self.domains[row]
        domain_key = f"{domain_data['domain']}_{domain_data['zone_id']}"
        
        # Get the button from the actions cell
        actions_widget = self.domains_table.cellWidget(row, 5)
        start_stop_btn = actions_widget.layout().itemAt(0).widget()
        
        if start_stop_btn.text() == 'Start':
            self.start_domain_update(row)
        else:
            self.stop_domain_update(row)

    def start_domain_update(self, row):
        """Start update for a domain at specified row"""
        if row < 0 or row >= len(self.domains):
            return
            
        domain_data = self.domains[row]
        domain_key = f"{domain_data['domain']}_{domain_data['zone_id']}"
        
        # Get UI elements
        actions_widget = self.domains_table.cellWidget(row, 5)
        start_stop_btn = actions_widget.layout().itemAt(0).widget()
        status_item = self.domains_table.item(row, 3)
        
        try:
            self.ip_updater.start_updating(
                domain_data['api_token'], 
                domain_data['zone_id'], 
                domain_data['domain'], 
                domain_data.get('interval', 15), 
                self.update_log_display
            )
            
            # Update UI
            start_stop_btn.setText('Stop')
            status_item.setText('Running')
            status_item.setForeground(QColor(0, 128, 0))  # Green for running
            
            # Track running status
            self.running_domains[domain_key] = True
            
            # Log start
            self.update_log_display(f"Started updates for {domain_data['domain']}")
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def stop_domain_update(self, row):
        """Stop update for a domain at specified row"""
        if row < 0 or row >= len(self.domains):
            return
            
        domain_data = self.domains[row]
        domain_key = f"{domain_data['domain']}_{domain_data['zone_id']}"
        
        # Get UI elements
        actions_widget = self.domains_table.cellWidget(row, 5)
        start_stop_btn = actions_widget.layout().itemAt(0).widget()
        status_item = self.domains_table.item(row, 3)
        
        try:
            self.ip_updater.stop_updating(domain_data['domain'], domain_data['zone_id'])
            
            # Update UI
            start_stop_btn.setText('Start')
            status_item.setText('Stopped')
            status_item.setForeground(QColor(255, 0, 0))  # Red for stopped
            
            # Track running status
            self.running_domains[domain_key] = False
            
            # Log stop
            self.update_log_display(f"Stopped updates for {domain_data['domain']}")
            
        except Exception as e:
            QMessageBox.critical(self, 'Error', str(e))

    def start_all_domains(self):
        """
        Start updates for all domains
        """
        for row in range(self.domains_table.rowCount()):
            self.start_domain_update(row)

    def stop_all_domains(self):
        """
        Stop updates for all domains
        """
        for row in range(self.domains_table.rowCount()):
            self.stop_domain_update(row)

    def manual_update_all_domains(self):
        """
        Manually trigger IP update for all domains
        """
        updated_domains = 0
        failed_domains = 0

        for row in range(self.domains_table.rowCount()):
            try:
                domain_data = self.domains[row]
                current_ip = self.ip_updater.get_current_ip()
                
                if current_ip:
                    success = self.ip_updater.update_cloudflare_dns(
                        domain_data['api_token'], 
                        domain_data['zone_id'], 
                        domain_data['domain'], 
                        current_ip
                    )
                    
                    if success:
                        updated_domains += 1
                        # Update Last Update time
                        now = datetime.datetime.now().strftime('%H:%M:%S')
                        self.domains_table.item(row, 4).setText(now)
                        
                        log_message = f"Manually updated {domain_data['domain']} to IP {current_ip}"
                        self.update_log_display(log_message)
                    else:
                        failed_domains += 1
                        log_message = f"Manual update failed for {domain_data['domain']}"
                        self.update_log_display(log_message)
                else:
                    failed_domains += 1
                    log_message = f"Could not retrieve current IP for {domain_data['domain']}"
                    self.update_log_display(log_message)
            except Exception as e:
                failed_domains += 1
                log_message = f"Error updating {domain_data['domain']}: {str(e)}"
                self.update_log_display(log_message)

        # Show summary message
        summary_message = f"Manual Update Complete. Updated: {updated_domains}, Failed: {failed_domains}"
        self.update_log_display(summary_message)
        QMessageBox.information(self, 'Manual Update', summary_message)

    def save_domains(self):
        """
        Save current domains to configuration
        """
        try:
            # Save domains to config file
            success = self.config_manager.save_config(self.domains)
            if success:
                # Quietly log successful save
                self.logger.info("Configuration saved successfully")
            else:
                self.update_log_display("Warning: Failed to save configuration")
        except Exception as e:
            self.update_log_display(f"Error saving configuration: {str(e)}")

    # Update the toggle_windows_startup method to use startup_checkbox instead of startup_action:

    def toggle_windows_startup(self, state):
        """
        Toggle Windows startup setting
        """
        try:
            if state == Qt.Checked:
                # Enable startup
                success = self.config_manager.set_windows_startup(True)
                if success:
                    self.update_log_display("Added application to Windows startup")
                else:
                    self.update_log_display("Failed to add to Windows startup")
            else:
                # Disable startup
                success = self.config_manager.set_windows_startup(False)
                if success:
                    self.update_log_display("Removed application from Windows startup")
                else:
                    self.update_log_display("Failed to remove from Windows startup")
                    
            # Update checkbox without triggering event
            if not success:
                self.startup_checkbox.blockSignals(True)
                self.startup_checkbox.setChecked(not state)
                self.startup_checkbox.blockSignals(False)
                
        except Exception as e:
            self.update_log_display(f"Error changing startup setting: {str(e)}")
            # Revert checkbox
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(not state)
            self.startup_checkbox.blockSignals(False)

    def update_log_display(self, message):
        """
        Update log display with new message
        """
        # Add timestamp to message
        timestamp = datetime.datetime.now().strftime('%H:%M:%S')
        formatted_message = f"[{timestamp}] {message}"
        
        # Use QTimer to update log display from main thread
        QTimer.singleShot(0, lambda: self._update_log(formatted_message))
        
        # Also log to the logger for file logging
        try:
            if hasattr(self, 'logger'):
                self.logger.info(message)
            else:
                # Fallback if logger isn't initialized yet
                print(message)
        except Exception as e:
            print(f"Logging error: {e}")
            print(message)
    
    def _update_log(self, message):
        """Update log text editor (must be called from main thread)"""
        self.log_display.append(message)
        # Scroll to bottom
        self.log_display.verticalScrollBar().setValue(
            self.log_display.verticalScrollBar().maximum()
        )
        
        # Limit log size to prevent memory issues (keep last 1000 lines)
        log_text = self.log_display.toPlainText()
        lines = log_text.split('\n')
        if len(lines) > 1000:
            self.log_display.setPlainText('\n'.join(lines[-1000:]))
            self.log_display.verticalScrollBar().setValue(
                self.log_display.verticalScrollBar().maximum()
            )

    def closeEvent(self, event):
        """
        Handle close event
        """
        if self.tray_icon.isVisible():
            # Only ask if the system tray is available
            reply = QMessageBox.question(
                self, 'Minimize', 
                'Do you want to minimize to system tray?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                event.ignore()
                self.hide()
                
                # Show tray notification
                self.tray_icon.showMessage(
                    'Cloudflare IP Updater',
                    'Application is still running in the system tray.',
                    QSystemTrayIcon.Information,
                    3000  # Show for 3 seconds
                )
                return
        
        # No system tray or user chose to exit
        self.close_application()

    def close_application(self):
        """
        Properly close the application
        """
        # Stop all domain updates
        self.ip_updater.stop_updating()
        
        # Save current domain configurations
        self.save_domains()
        
        # Clean up timers
        self.auto_save_timer.stop()
        self.ip_display_timer.stop()
        
        # Log application exit
        self.logger.info("Application closed")
        
        # Quit the application
        QApplication.quit()

def main():
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName('Cloudflare IP Updater')
    app.setQuitOnLastWindowClosed(False)  # Allow minimize to tray

    # Create and show main window
    main_window = MainApplication()
    main_window.show()

    # Run the application
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()