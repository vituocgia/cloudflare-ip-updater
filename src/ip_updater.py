import threading
import time
import logging
import requests
import json

class CloudflareIPUpdater:
    def __init__(self):
        self._update_thread = None
        self._is_running = False
        self._logger = logging.getLogger(__name__)
        self._current_ip = None
        self._update_callback = None
        self._active_domains = {}  # Track active updating domains
        self._domain_ips = {}  # Store IPs for each domain separately

    def get_current_ip(self):
        """
        Retrieve current public IP address
        
        :return: Current public IP address
        """
        try:
            # Try multiple services in case one fails
            services = [
                'https://api.ipify.org?format=json',
                'https://ifconfig.me/ip',
                'https://icanhazip.com/'
            ]
            
            for service in services:
                try:
                    if 'ipify' in service:
                        response = requests.get(service, timeout=10)
                        return response.json()['ip']
                    else:
                        response = requests.get(service, timeout=10)
                        return response.text.strip()
                except Exception as e:
                    self._logger.warning(f"Failed to get IP from {service}: {e}")
                    continue
                    
            self._logger.error("All IP services failed")
            return None
        except Exception as e:
            self._logger.error(f"Error getting current IP: {e}")
            return None

    def get_cloudflare_dns_record(self, api_token, zone_id, domain):
        """
        Retrieve existing Cloudflare DNS record details
        """
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        params = {"type": "A", "name": domain}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            data = response.json()
            
            if data.get('success') and data.get('result'):
                return data['result'][0]
            else:
                error_msg = data.get('errors', [{'message': 'Unknown error'}])[0].get('message', 'Failed to retrieve DNS record')
                self._logger.error(f"Cloudflare API error: {error_msg}")
                return None
        except Exception as e:
            self._logger.error(f"Error retrieving DNS record: {e}")
            return None

    def update_cloudflare_dns(self, api_token, zone_id, domain, current_ip):
        """
        Update Cloudflare DNS record with current IP
        
        :return: True if update successful, False otherwise
        """
        record = self.get_cloudflare_dns_record(api_token, zone_id, domain)
        if not record:
            return False

        # Check if the current DNS record already matches the IP
        if record.get('content') == current_ip:
            self._logger.info(f"IP unchanged for {domain}: {current_ip}")
            return True  # Return True since record is already up to date

        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record['id']}"
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        # Preserve existing settings like proxied status
        payload = {
            "type": "A",
            "name": domain,
            "content": current_ip,
            "ttl": record.get('ttl', 1),  # Keep existing TTL or use Auto TTL
            "proxied": record.get('proxied', True)  # Keep existing proxied setting
        }

        try:
            response = requests.put(url, headers=headers, data=json.dumps(payload), timeout=10)
            result = response.json()
            
            if result.get('success'):
                self._logger.info(f"Successfully updated {domain} to {current_ip}")
                return True
            else:
                error_msg = result.get('errors', [{'message': 'Unknown error'}])[0].get('message', 'Failed to update DNS record')
                self._logger.error(f"Cloudflare API error: {error_msg}")
                return False
        except Exception as e:
            self._logger.error(f"Error updating DNS record: {e}")
            return False

    def test_connection(self, api_token, zone_id, domain):
        """
        Test Cloudflare API connection and DNS record retrieval
        """
        try:
            # Get current IP
            current_ip = self.get_current_ip()
            if not current_ip:
                return False, "Failed to retrieve current IP address"

            # Try to retrieve DNS record
            record = self.get_cloudflare_dns_record(api_token, zone_id, domain)
            if not record:
                return False, "Failed to retrieve DNS record from Cloudflare"

            return True, f"Connection successful. Current record: {record.get('content', 'unknown')}"
        except Exception as e:
            self._logger.error(f"Connection test failed: {e}")
            return False, f"Connection test failed: {str(e)}"

    def _update_ip_thread(self, api_token, zone_id, domain, interval, log_callback):
        """
        Background thread to update IP periodically
        """
        domain_key = f"{domain}_{zone_id}"
        self._active_domains[domain_key] = True
        
        # Initial status log
        log_message = f"Starting update thread for {domain} with {interval} minute interval"
        self._logger.info(log_message)
        if log_callback:
            log_callback(log_message)
        
        check_count = 0
        
        while self._active_domains.get(domain_key, False):
            try:
                check_count += 1
                # Get current IP
                current_ip = self.get_current_ip()
                # Get stored IP for this specific domain
                stored_ip = self._domain_ips.get(domain_key)
                
                # Log IP check - even when no change occurs (for visibility)
                log_message = f"Check #{check_count}: Checking IP for {domain}..."
                self._logger.info(log_message)
                if log_callback:
                    log_callback(log_message)
                
                if current_ip:
                    if stored_ip is None:
                        log_message = f"Initial IP for {domain} is {current_ip}"
                        self._logger.info(log_message)
                        if log_callback:
                            log_callback(log_message)
                    
                    # Check if IP has changed or this is first run
                    if stored_ip is None or current_ip != stored_ip:
                        log_message = f"IP change detected for {domain}: {stored_ip if stored_ip else 'None'} -> {current_ip}"
                        self._logger.info(log_message)
                        if log_callback:
                            log_callback(log_message)
                        
                        # Update Cloudflare DNS
                        success = self.update_cloudflare_dns(api_token, zone_id, domain, current_ip)
                        
                        # Log the result
                        if success:
                            log_message = f"Successfully updated {domain} DNS record to {current_ip}"
                            self._logger.info(log_message)
                            if log_callback:
                                log_callback(log_message)
                            
                            # Update stored IP for this domain
                            self._domain_ips[domain_key] = current_ip
                        else:
                            log_message = f"Failed to update {domain} DNS record to {current_ip}"
                            self._logger.warning(log_message)
                            if log_callback:
                                log_callback(log_message)
                    else:
                        log_message = f"No IP change for {domain}, still {current_ip}"
                        self._logger.info(log_message)
                        if log_callback:
                            log_callback(log_message)
                else:
                    log_message = f"Failed to retrieve current IP for {domain}"
                    self._logger.warning(log_message)
                    if log_callback:
                        log_callback(log_message)
                
                # Sleep for specified interval
                log_message = f"Next check for {domain} in {interval} minutes"
                self._logger.info(log_message)
                if log_callback:
                    log_callback(log_message)
                    
                # Check every 10 seconds if we should stop
                for i in range(interval * 6):  
                    if not self._active_domains.get(domain_key, False):
                        break
                    time.sleep(10)
            
            except Exception as e:
                log_message = f"Error in update thread for {domain}: {e}"
                self._logger.error(log_message)
                if log_callback:
                    log_callback(log_message)
                
                # Sleep to prevent rapid error loops
                time.sleep(30)
        
        # Log when thread stops
        log_message = f"Update thread for {domain} stopped"
        self._logger.info(log_message)
        if log_callback:
            log_callback(log_message)

    def start_updating(self, api_token, zone_id, domain, interval, log_callback=None):
        """
        Start the IP update process
        """
        # Create domain key for tracking
        domain_key = f"{domain}_{zone_id}"
        
        # Stop if already running
        if domain_key in self._active_domains and self._active_domains[domain_key]:
            self.stop_updating(domain, zone_id)
        
        # Set domain as active
        self._active_domains[domain_key] = True

        # Create and start update thread
        thread = threading.Thread(
            target=self._update_ip_thread, 
            args=(api_token, zone_id, domain, interval, log_callback),
            daemon=True
        )
        thread.start()
        
        # Log startup
        log_message = f"Started IP updating for {domain} with {interval} minute interval"
        self._logger.info(log_message)
        if log_callback:
            log_callback(log_message)

    def stop_updating(self, domain=None, zone_id=None):
        """
        Stop the IP update process
        """
        if domain and zone_id:
            # Stop specific domain
            domain_key = f"{domain}_{zone_id}"
            if domain_key in self._active_domains:
                self._active_domains[domain_key] = False
        else:
            # Stop all domains
            for key in list(self._active_domains.keys()):
                self._active_domains[key] = False