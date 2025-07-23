#!/usr/bin/env python3
"""
Shuttle Security Audit Tool

Validates production deployment security configuration by checking:
- User accounts against expected configuration
- Group memberships and restrictions  
- File and directory permissions
- Samba user security model compliance
- Path permissions from shuttle configuration

Usage:
    python3 scripts/security_audit.py --audit-config /path/to/audit_config.yaml --shuttle-config /path/to/shuttle_config.yaml
    python3 scripts/security_audit.py --help
"""

import argparse
import os
import sys
import yaml
import pwd
import grp
import stat
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field


@dataclass
class AuditResult:
    """Container for audit check results"""
    passed: bool
    message: str
    details: List[str] = field(default_factory=list)
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL


@dataclass  
class AuditSummary:
    """Summary of all audit results"""
    total_checks: int = 0
    passed: int = 0
    warnings: int = 0
    errors: int = 0
    critical: int = 0
    results: List[AuditResult] = field(default_factory=list)


class SecurityAuditor:
    """Main security audit class"""
    
    def __init__(self, audit_config_path: str, shuttle_config_path: str):
        self.audit_config_path = audit_config_path
        self.shuttle_config_path = shuttle_config_path
        self.audit_config: Dict[str, Any] = {}
        self.shuttle_config: Dict[str, Any] = {}
        self.summary = AuditSummary()
        
    def load_configs(self) -> bool:
        """Load audit and shuttle configuration files"""
        try:
            with open(self.audit_config_path, 'r') as f:
                self.audit_config = yaml.safe_load(f)
            print(f"✓ Loaded audit config: {self.audit_config_path}")
            
            with open(self.shuttle_config_path, 'r') as f:
                self.shuttle_config = yaml.safe_load(f)
            print(f"✓ Loaded shuttle config: {self.shuttle_config_path}")
            
            return True
            
        except FileNotFoundError as e:
            print(f"❌ Config file not found: {e}")
            return False
        except yaml.YAMLError as e:
            print(f"❌ YAML parsing error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading configs: {e}")
            return False
    
    def run_audit(self) -> AuditSummary:
        """Run complete security audit"""
        print("=" * 60)
        print("🔒 Shuttle Security Audit")
        print("=" * 60)
        
        if not self.load_configs():
            return self.summary
            
        # Run audit sections
        self._audit_users()
        self._audit_groups() 
        self._audit_samba_security()
        self._audit_path_permissions()
        self._audit_file_permissions()
        
        return self.summary
    
    def _add_result(self, check_name: str, passed: bool, message: str, 
                   details: List[str] = None, severity: str = "INFO"):
        """Add audit result to summary"""
        result = AuditResult(
            passed=passed,
            message=f"{check_name}: {message}",
            details=details or [],
            severity=severity
        )
        
        self.summary.results.append(result)
        self.summary.total_checks += 1
        
        if passed:
            self.summary.passed += 1
        else:
            if severity == "WARNING":
                self.summary.warnings += 1
            elif severity == "ERROR":
                self.summary.errors += 1
            elif severity == "CRITICAL":
                self.summary.critical += 1
    
    def _audit_users(self):
        """Audit user accounts against expected configuration"""
        print("\n🔍 Auditing Users...")
        
        expected_users = self.audit_config.get('users', [])
        if not expected_users:
            self._add_result("User Configuration", False, 
                           "No users defined in audit config", severity="WARNING")
            return
        
        for user_config in expected_users:
            username = user_config['name']
            self._audit_single_user(username, user_config)
    
    def _audit_single_user(self, username: str, expected_config: Dict[str, Any]):
        """Audit a single user account"""
        try:
            user_info = pwd.getpwnam(username)
            
            # Check account type expectations
            account_type = expected_config.get('account_type', 'unknown')
            shell = user_info.pw_shell
            
            if account_type == 'service':
                # Service accounts should have nologin shells
                if shell not in ['/usr/sbin/nologin', '/bin/false', '/sbin/nologin']:
                    self._add_result(f"User {username} Shell", False,
                                   f"Service account has login shell: {shell}",
                                   severity="ERROR")
                else:
                    self._add_result(f"User {username} Shell", True,
                                   f"Service account properly restricted: {shell}")
            
            # Check group memberships
            expected_groups = expected_config.get('groups', {})
            self._audit_user_groups(username, user_info, expected_groups)
            
            # Check home directory
            if expected_config.get('source') == 'local':
                expected_home = expected_config.get('home_directory')
                if expected_home and user_info.pw_dir != expected_home:
                    self._add_result(f"User {username} Home", False,
                                   f"Home directory mismatch: expected {expected_home}, got {user_info.pw_dir}",
                                   severity="WARNING")
                else:
                    self._add_result(f"User {username} Home", True,
                                   f"Home directory correct: {user_info.pw_dir}")
                                   
        except KeyError:
            self._add_result(f"User {username} Existence", False,
                           f"User {username} does not exist", severity="ERROR")
    
    def _audit_user_groups(self, username: str, user_info, expected_groups: Dict[str, Any]):
        """Audit user group memberships"""
        try:
            # Get actual groups
            actual_primary_gid = user_info.pw_gid
            actual_primary_group = grp.getgrgid(actual_primary_gid).gr_name
            
            # Get all groups user belongs to
            actual_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
            actual_groups.append(actual_primary_group)  # Add primary group
            actual_groups = set(actual_groups)
            
            # Check primary group
            expected_primary = expected_groups.get('primary')
            if expected_primary:
                if actual_primary_group == expected_primary:
                    self._add_result(f"User {username} Primary Group", True,
                                   f"Primary group correct: {actual_primary_group}")
                else:
                    self._add_result(f"User {username} Primary Group", False,
                                   f"Primary group mismatch: expected {expected_primary}, got {actual_primary_group}",
                                   severity="ERROR")
            
            # Check secondary groups
            expected_secondary = set(expected_groups.get('secondary', []))
            actual_secondary = actual_groups - {actual_primary_group}
            
            missing_groups = expected_secondary - actual_secondary
            extra_groups = actual_secondary - expected_secondary
            
            if missing_groups:
                self._add_result(f"User {username} Missing Groups", False,
                               f"Missing secondary groups: {', '.join(missing_groups)}",
                               severity="ERROR")
            
            if extra_groups:
                self._add_result(f"User {username} Extra Groups", False,
                               f"Unexpected secondary groups: {', '.join(extra_groups)}",
                               severity="WARNING")
            
            if not missing_groups and not extra_groups:
                self._add_result(f"User {username} Secondary Groups", True,
                               f"Secondary groups correct: {', '.join(actual_secondary) if actual_secondary else 'None'}")
                               
        except Exception as e:
            self._add_result(f"User {username} Groups", False,
                           f"Error checking groups: {e}", severity="ERROR")
    
    def _audit_groups(self):
        """Audit group configurations"""
        print("\n🔍 Auditing Groups...")
        
        expected_groups = self.audit_config.get('groups', [])
        if not expected_groups:
            self._add_result("Group Configuration", False,
                           "No groups defined in audit config", severity="WARNING")
            return
        
        for group_config in expected_groups:
            group_name = group_config['name']
            self._audit_single_group(group_name, group_config)
    
    def _audit_single_group(self, group_name: str, expected_config: Dict[str, Any]):
        """Audit a single group"""
        try:
            group_info = grp.getgrnam(group_name)
            
            # Check GID if specified
            expected_gid = expected_config.get('gid')
            if expected_gid is not None:
                if group_info.gr_gid == expected_gid:
                    self._add_result(f"Group {group_name} GID", True,
                                   f"GID correct: {group_info.gr_gid}")
                else:
                    self._add_result(f"Group {group_name} GID", False,
                                   f"GID mismatch: expected {expected_gid}, got {group_info.gr_gid}",
                                   severity="WARNING")
            
            # Check members if specified
            expected_members = set(expected_config.get('members', []))
            actual_members = set(group_info.gr_mem)
            
            missing_members = expected_members - actual_members
            extra_members = actual_members - expected_members
            
            if missing_members:
                self._add_result(f"Group {group_name} Missing Members", False,
                               f"Missing members: {', '.join(missing_members)}",
                               severity="ERROR")
            
            if extra_members:
                # Check if extra members are allowed
                allow_extra = expected_config.get('allow_extra_members', False)
                severity = "WARNING" if allow_extra else "ERROR"
                self._add_result(f"Group {group_name} Extra Members", not allow_extra,
                               f"Extra members: {', '.join(extra_members)}",
                               severity=severity)
            
            if not missing_members and (not extra_members or expected_config.get('allow_extra_members', False)):
                self._add_result(f"Group {group_name} Members", True,
                               f"Members correct: {', '.join(actual_members) if actual_members else 'None'}")
                               
        except KeyError:
            self._add_result(f"Group {group_name} Existence", False,
                           f"Group {group_name} does not exist", severity="ERROR")
    
    def _audit_samba_security(self):
        """Audit Samba-specific security requirements"""
        print("\n🔍 Auditing Samba Security Model...")
        
        samba_config = self.audit_config.get('samba_security', {})
        if not samba_config:
            self._add_result("Samba Security Config", False,
                           "No Samba security configuration found", severity="WARNING")
            return
        
        # Check Samba user restrictions
        for samba_group in ['shuttle_samba_in_users', 'shuttle_out_users']:
            if samba_group in samba_config:
                self._audit_samba_group_restrictions(samba_group, samba_config[samba_group])
    
    def _audit_samba_group_restrictions(self, group_name: str, restrictions: Dict[str, Any]):
        """Audit restrictions for Samba user groups"""
        try:
            group_info = grp.getgrnam(group_name)
            samba_users = group_info.gr_mem
            
            for username in samba_users:
                # Check shell restrictions
                user_info = pwd.getpwnam(username)
                allowed_shells = restrictions.get('allowed_shells', ['/usr/sbin/nologin', '/bin/false'])
                
                if user_info.pw_shell not in allowed_shells:
                    self._add_result(f"Samba User {username} Shell", False,
                                   f"Samba user has interactive shell: {user_info.pw_shell}",
                                   severity="CRITICAL")
                else:
                    self._add_result(f"Samba User {username} Shell", True,
                                   f"Samba user properly restricted: {user_info.pw_shell}")
                
                # Check group isolation
                user_groups = [g.gr_name for g in grp.getgrall() if username in g.gr_mem]
                user_groups.append(grp.getgrgid(user_info.pw_gid).gr_name)  # Add primary
                
                forbidden_groups = restrictions.get('forbidden_groups', [])
                violations = [g for g in user_groups if g in forbidden_groups]
                
                if violations:
                    self._add_result(f"Samba User {username} Group Isolation", False,
                                   f"Samba user in forbidden groups: {', '.join(violations)}",
                                   severity="CRITICAL")
                else:
                    self._add_result(f"Samba User {username} Group Isolation", True,
                                   f"Samba user properly isolated from other groups")
                                   
        except KeyError as e:
            self._add_result(f"Samba Group {group_name}", False,
                           f"Group not found: {e}", severity="ERROR")
        except Exception as e:
            self._add_result(f"Samba Group {group_name}", False,
                           f"Error auditing Samba group: {e}", severity="ERROR")
    
    def _audit_path_permissions(self):
        """Audit path permissions from shuttle configuration"""
        print("\n🔍 Auditing Path Permissions...")
        
        # Get paths from shuttle config
        shuttle_paths = self._extract_shuttle_paths()
        if not shuttle_paths:
            self._add_result("Shuttle Paths", False,
                           "No paths found in shuttle configuration", severity="WARNING")
            return
        
        for path_name, path_config in shuttle_paths.items():
            self._audit_single_path(path_name, path_config)
    
    def _extract_shuttle_paths(self) -> Dict[str, Dict[str, Any]]:
        """Extract paths from shuttle configuration"""
        paths = {}
        
        # Standard shuttle paths
        config_paths = {
            'source': self.shuttle_config.get('source_path'),
            'destination': self.shuttle_config.get('destination_path'), 
            'quarantine': self.shuttle_config.get('quarantine_path'),
            'hazard_archive': self.shuttle_config.get('hazard_archive_path'),
            'tracking': self.shuttle_config.get('tracking_path')
        }
        
        for name, path in config_paths.items():
            if path:
                paths[name] = {'path': path, 'type': 'shuttle_path'}
        
        return paths
    
    def _audit_single_path(self, path_name: str, path_config: Dict[str, Any]):
        """Audit permissions for a single path"""
        path_str = path_config['path']
        path_obj = Path(path_str)
        
        if not path_obj.exists():
            self._add_result(f"Path {path_name}", False,
                           f"Path does not exist: {path_str}", severity="ERROR")
            return
        
        try:
            stat_info = path_obj.stat()
            
            # Check ownership and permissions
            self._check_path_ownership(path_name, path_obj, stat_info)
            self._check_path_permissions(path_name, path_obj, stat_info)
            self._check_path_security(path_name, path_obj)
            
        except Exception as e:
            self._add_result(f"Path {path_name}", False,
                           f"Error auditing path {path_str}: {e}", severity="ERROR")
    
    def _check_path_ownership(self, path_name: str, path_obj: Path, stat_info):
        """Check path ownership"""
        try:
            owner = pwd.getpwuid(stat_info.st_uid).pw_name
            group = grp.getgrgid(stat_info.st_gid).gr_name
            
            # Get expected ownership from audit config
            expected_ownership = self.audit_config.get('path_ownership', {}).get(path_name, {})
            expected_owner = expected_ownership.get('owner')
            expected_group = expected_ownership.get('group')
            
            if expected_owner and owner != expected_owner:
                self._add_result(f"Path {path_name} Owner", False,
                               f"Owner mismatch: expected {expected_owner}, got {owner}",
                               severity="ERROR")
            elif expected_owner:
                self._add_result(f"Path {path_name} Owner", True,
                               f"Owner correct: {owner}")
            
            if expected_group and group != expected_group:
                self._add_result(f"Path {path_name} Group", False,
                               f"Group mismatch: expected {expected_group}, got {group}",
                               severity="ERROR")
            elif expected_group:
                self._add_result(f"Path {path_name} Group", True,
                               f"Group correct: {group}")
                               
        except Exception as e:
            self._add_result(f"Path {path_name} Ownership", False,
                           f"Error checking ownership: {e}", severity="ERROR")
    
    def _check_path_permissions(self, path_name: str, path_obj: Path, stat_info):
        """Check path permissions"""
        mode = stat_info.st_mode
        perms = stat.filemode(mode)
        octal_perms = oct(stat.S_IMODE(mode))
        
        # Check for world-readable files (security risk)
        if mode & stat.S_IROTH:
            self._add_result(f"Path {path_name} World Readable", False,
                           f"Path is world-readable: {perms} ({octal_perms})",
                           severity="CRITICAL")
        else:
            self._add_result(f"Path {path_name} World Readable", True,
                           f"Path not world-readable: {perms} ({octal_perms})")
        
        # Check for executable files in data directories
        if path_obj.is_file() and (mode & stat.S_IXUSR or mode & stat.S_IXGRP or mode & stat.S_IXOTH):
            if path_name in ['source', 'destination', 'quarantine']:
                self._add_result(f"Path {path_name} Executable", False,
                               f"Executable file in data directory: {perms} ({octal_perms})",
                               severity="WARNING")
    
    def _check_path_security(self, path_name: str, path_obj: Path):
        """Check additional path security measures"""
        # Check for ACLs if getfacl is available
        try:
            result = subprocess.run(['getfacl', str(path_obj)], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                acl_output = result.stdout
                if 'default:' in acl_output and path_obj.is_dir():
                    self._add_result(f"Path {path_name} Default ACLs", True,
                                   "Default ACLs present for directory")
                else:
                    self._add_result(f"Path {path_name} Default ACLs", False,
                                   "No default ACLs found for directory",
                                   severity="WARNING")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            # getfacl not available or timeout
            pass
        except Exception as e:
            self._add_result(f"Path {path_name} ACL Check", False,
                           f"Error checking ACLs: {e}", severity="INFO")
    
    def _audit_file_permissions(self):
        """Audit file permissions in shuttle directories"""
        print("\n🔍 Auditing File Permissions...")
        
        shuttle_paths = self._extract_shuttle_paths()
        
        for path_name, path_config in shuttle_paths.items():
            path_str = path_config['path']
            if os.path.exists(path_str):
                self._scan_directory_permissions(path_name, path_str)
    
    def _scan_directory_permissions(self, path_name: str, directory: str, max_files: int = 100):
        """Scan directory for permission issues"""
        issues_found = 0
        files_checked = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                # Check directories
                for dirname in dirs[:10]:  # Limit to avoid excessive output
                    dir_path = os.path.join(root, dirname)
                    try:
                        stat_info = os.stat(dir_path)
                        if stat_info.st_mode & stat.S_IROTH:
                            issues_found += 1
                            self._add_result(f"Directory Permissions {path_name}", False,
                                           f"World-readable directory: {dir_path}",
                                           severity="WARNING")
                    except OSError:
                        continue
                
                # Check files
                for filename in files[:max_files]:
                    if files_checked >= max_files:
                        break
                    
                    file_path = os.path.join(root, filename)
                    try:
                        stat_info = os.stat(file_path)
                        
                        # Check for world-readable files
                        if stat_info.st_mode & stat.S_IROTH:
                            issues_found += 1
                            self._add_result(f"File Permissions {path_name}", False,
                                           f"World-readable file: {file_path}",
                                           severity="WARNING")
                        
                        # Check for executable files in data directories
                        if path_name in ['source', 'destination', 'quarantine']:
                            if stat_info.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
                                issues_found += 1
                                self._add_result(f"File Executable {path_name}", False,
                                               f"Executable file in data directory: {file_path}",
                                               severity="WARNING")
                        
                        files_checked += 1
                        
                    except OSError:
                        continue
                
                if files_checked >= max_files:
                    break
        
        except Exception as e:
            self._add_result(f"Directory Scan {path_name}", False,
                           f"Error scanning directory {directory}: {e}", severity="ERROR")
            return
        
        if issues_found == 0 and files_checked > 0:
            self._add_result(f"Directory Security {path_name}", True,
                           f"No permission issues found in {files_checked} files checked")
    
    def print_results(self):
        """Print audit results"""
        print("\n" + "=" * 60)
        print("📊 AUDIT RESULTS")
        print("=" * 60)
        
        # Group results by severity
        criticals = [r for r in self.summary.results if r.severity == "CRITICAL" and not r.passed]
        errors = [r for r in self.summary.results if r.severity == "ERROR" and not r.passed]
        warnings = [r for r in self.summary.results if r.severity == "WARNING" and not r.passed]
        passed = [r for r in self.summary.results if r.passed]
        
        # Print critical issues first
        if criticals:
            print(f"\n🚨 CRITICAL ISSUES ({len(criticals)}):")
            for result in criticals:
                print(f"  ❌ {result.message}")
                for detail in result.details:
                    print(f"     {detail}")
        
        # Print errors
        if errors:
            print(f"\n❌ ERRORS ({len(errors)}):")
            for result in errors:
                print(f"  ❌ {result.message}")
                for detail in result.details:
                    print(f"     {detail}")
        
        # Print warnings
        if warnings:
            print(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for result in warnings:
                print(f"  ⚠️  {result.message}")
                for detail in result.details:
                    print(f"     {detail}")
        
        # Print summary
        print(f"\n📈 SUMMARY:")
        print(f"  Total checks: {self.summary.total_checks}")
        print(f"  ✅ Passed: {self.summary.passed}")
        print(f"  ⚠️  Warnings: {self.summary.warnings}")
        print(f"  ❌ Errors: {self.summary.errors}")
        print(f"  🚨 Critical: {self.summary.critical}")
        
        # Overall status
        if self.summary.critical > 0:
            print(f"\n🚨 AUDIT STATUS: CRITICAL - Immediate attention required!")
            return 2
        elif self.summary.errors > 0:
            print(f"\n❌ AUDIT STATUS: FAILED - Configuration issues found")
            return 1
        elif self.summary.warnings > 0:
            print(f"\n⚠️  AUDIT STATUS: WARNINGS - Review recommended")
            return 0
        else:
            print(f"\n✅ AUDIT STATUS: PASSED - Security configuration verified")
            return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Shuttle Security Audit Tool')
    parser.add_argument('--audit-config', required=True,
                       help='Path to audit configuration YAML file')
    parser.add_argument('--shuttle-config', required=True,
                       help='Path to shuttle configuration YAML file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Create auditor and run audit
    auditor = SecurityAuditor(args.audit_config, args.shuttle_config)
    summary = auditor.run_audit()
    
    # Print results and exit with appropriate code
    exit_code = auditor.print_results()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()