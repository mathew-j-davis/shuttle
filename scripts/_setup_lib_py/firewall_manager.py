#!/usr/bin/env python3
"""
Firewall Manager
Manages firewall configuration from YAML
"""

import yaml
import sys
from typing import Dict, List, Any

# Handle both relative and absolute imports
try:
    from .command_executor import run_command
    from .config_analyzer import analyze_config
except ImportError:
    from command_executor import run_command
    from config_analyzer import analyze_config


class FirewallManager:
    """Manages firewall configuration from YAML"""
    
    def __init__(self, production_dir: str, dry_run: bool = False, non_interactive: bool = False):
        """
        Initialize the firewall manager
        
        Args:
            production_dir: Path to production scripts directory
            dry_run: If True, only show what would be done
            non_interactive: If True, skip operations requiring user input
        """
        self.production_dir = production_dir
        self.dry_run = dry_run
        self.non_interactive = non_interactive
        self.firewall_script = f"{production_dir}/14_configure_firewall.sh"
    
    def process_config(self, config_file: str) -> bool:
        """
        Process firewall configuration from YAML file
        
        Args:
            config_file: Path to YAML configuration file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load YAML configuration
            with open(config_file, 'r') as f:
                docs = list(yaml.safe_load_all(f))
            
            if not docs:
                print("No configuration documents found")
                return False
            
            # Main config should be first document
            main_config = docs[0]
            firewall_config = main_config.get('firewall', {})
            
            if not firewall_config.get('enabled', False):
                print("ℹ️  Firewall configuration is disabled")
                return True
            
            print("🛡️ Configuring firewall...")
            return self._configure_firewall(firewall_config)
            
        except Exception as e:
            print(f"❌ Error processing firewall configuration: {e}")
            return False
    
    def _configure_firewall(self, config: Dict[str, Any]) -> bool:
        """Configure firewall based on configuration"""
        success = True
        
        # Enable firewall with default policies
        if not self._enable_firewall(config):
            success = False
        
        # Configure firewall rules
        if not self._configure_rules(config):
            success = False
        
        # Configure network topology rules
        if not self._configure_network_topology(config):
            success = False
        
        return success
    
    def _enable_firewall(self, config: Dict[str, Any]) -> bool:
        """Enable firewall with default policies"""
        try:
            print("🔧 Enabling firewall...")
            
            # Build enable command
            cmd = [self.firewall_script, "enable-firewall"]
            
            # Add default policy
            default_policy = config.get('default_policy', {})
            incoming_policy = default_policy.get('incoming', 'deny')
            cmd.extend(['--default-policy', incoming_policy])
            
            # Add logging level
            logging_level = config.get('logging', 'low')
            cmd.extend(['--logging', logging_level])
            
            # Add dry-run flag if needed
            if self.dry_run:
                cmd.append('--dry-run')
            
            return run_command(cmd, "Enable firewall with default policies")
            
        except Exception as e:
            print(f"❌ Error enabling firewall: {e}")
            return False
    
    def _configure_rules(self, config: Dict[str, Any]) -> bool:
        """Configure specific firewall rules"""
        try:
            rules = config.get('rules', {})
            if not rules:
                print("ℹ️  No specific firewall rules to configure")
                return True
            
            print("🔧 Configuring firewall rules...")
            success = True
            
            for rule_name, rule_config in rules.items():
                if not self._configure_rule(rule_name, rule_config):
                    success = False
            
            return success
            
        except Exception as e:
            print(f"❌ Error configuring firewall rules: {e}")
            return False
    
    def _configure_rule(self, rule_name: str, rule_config: Dict[str, Any]) -> bool:
        """Configure a specific firewall rule"""
        try:
            service = rule_config.get('service')
            action = rule_config.get('action', 'allow')
            sources = rule_config.get('sources', [])
            comment = rule_config.get('comment', f'{rule_name} rule')
            
            if not service:
                print(f"⚠️  Skipping rule '{rule_name}': no service specified")
                return True
            
            if not sources or sources == ['any']:
                print(f"ℹ️  Rule '{rule_name}': allowing from any source")
                sources = []
            
            # Configure rule for each source
            for source in sources:
                cmd = [self.firewall_script, f"{action}-{service}-from", "--source", source]
                
                if comment:
                    cmd.extend(['--comment', comment])
                
                if self.dry_run:
                    cmd.append('--dry-run')
                
                if not run_command(cmd, f"Configure {rule_name} for {source}"):
                    return False
            
            # If no sources specified, allow from any
            if not sources:
                if service == 'samba':
                    # For Samba, we use the generic service command
                    cmd = [self.firewall_script, "allow-service-from", "--service", "samba", "--source", "any"]
                elif service == 'ssh':
                    # SSH can use UFW's built-in rule
                    cmd = ["sudo", "ufw", "allow", "ssh"]
                else:
                    # Generic service
                    cmd = [self.firewall_script, "allow-service-from", "--service", service, "--source", "any"]
                
                if self.dry_run:
                    cmd.append('--dry-run')
                
                if not run_command(cmd, f"Configure {rule_name} from any source"):
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ Error configuring rule '{rule_name}': {e}")
            return False
    
    def _configure_network_topology(self, config: Dict[str, Any]) -> bool:
        """Configure network topology-based rules"""
        try:
            topology = config.get('network_topology', {})
            if not topology:
                print("ℹ️  No network topology configuration")
                return True
            
            print("🌐 Configuring network topology rules...")
            
            # Configure isolated hosts
            isolated_hosts = topology.get('isolated_hosts', [])
            for host in isolated_hosts:
                cmd = [self.firewall_script, "isolate-host", "--host", host]
                
                if self.dry_run:
                    cmd.append('--dry-run')
                
                if not run_command(cmd, f"Isolate host {host}"):
                    print(f"⚠️  Failed to isolate host {host}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error configuring network topology: {e}")
            return False


def main():
    """Main entry point for command-line usage"""
    if len(sys.argv) < 3:
        print("Usage: python3 -m firewall_manager <config_file> <production_dir> [--dry-run] [--non-interactive]")
        sys.exit(1)
    
    config_file = sys.argv[1]
    production_dir = sys.argv[2]
    
    # Parse options
    dry_run = '--dry-run' in sys.argv
    non_interactive = '--non-interactive' in sys.argv
    
    # Create manager and process configuration
    manager = FirewallManager(production_dir, dry_run, non_interactive)
    success = manager.process_config(config_file)
    
    if success:
        print("✅ Firewall configuration completed successfully")
        sys.exit(0)
    else:
        print("❌ Firewall configuration failed")
        sys.exit(1)


if __name__ == '__main__':
    main()