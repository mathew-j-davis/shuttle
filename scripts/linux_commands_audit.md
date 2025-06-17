# Linux Commands Audit Report

This document lists all Linux commands found in the post-install configuration scripts, categorized by execution method.

## Summary
- **Total files analyzed**: 25+ files
- **Bare commands**: 80+ instances (direct execution)
- **execute_or_dryrun commands**: 35+ instances (with dry-run support)
- **execute commands**: 0 instances (none found)

---

## BARE COMMANDS (Direct Execution)

### /home/mathew/shuttle/scripts/2_post_install_config.sh
- **Line 130**: `python3 -c "import yaml; list(yaml.safe_load_all(open('$CONFIG_FILE')))"` - YAML validation
- **Line 147**: `command -v python3 >/dev/null 2>&1` - Check Python availability
- **Line 154**: `python3 -c "import yaml"` - Check PyYAML availability
- **Line 181**: `chmod +x "$PRODUCTION_DIR/$script"` - Make scripts executable
- **Line 281**: `"$cmd" $install_flags` - Execute install script
- **Line 384**: `"$PRODUCTION_DIR/14_configure_firewall.sh" show-status` - Check firewall

### /home/mathew/shuttle/scripts/2_post_install_config_steps/11_install_tools.sh
- **Line 63**: `command -v apt-get >/dev/null 2>&1` - Detect package manager
- **Line 65**: `command -v dnf >/dev/null 2>&1` - Detect package manager
- **Line 67**: `command -v yum >/dev/null 2>&1` - Detect package manager
- **Line 187**: `dpkg -l "$package" >/dev/null 2>&1` - Check package installation
- **Line 190**: `rpm -q "$package" >/dev/null 2>&1` - Check package installation
- **Line 270**: `command -v sudo >/dev/null 2>&1` - Check sudo availability

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_common_.source.sh
- **Line 29**: `check_command "logger"` - Check logger availability
- **Line 30**: `logger -t "user-group-manager" "[$level] $message"` - System logging
- **Line 130**: `eval "$cmd"` - Execute command in execute_or_dryrun
- **Line 155**: `eval "$cmd"` - Execute command in execute
- **Line 179**: `command -v "$cmd" >/dev/null 2>&1` - Command existence check

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_check_active_user.source.sh
- **Line 25**: `sudo -n -v 2>/dev/null` - Check sudo authentication
- **Line 32**: `groups 2>/dev/null | grep -qE "(sudo|wheel|admin)"` - Check user groups

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_delete_user.source.sh
- **Line 155**: `who | grep -q "^$username "` - Check if user logged in
- **Line 162**: `getent passwd "$username" 2>/dev/null` - Check user exists
- **Line 210**: `find /home /var /opt /usr/local -user "$username" 2>/dev/null` - Find user files
- **Line 266**: `getent passwd "$domain_user" 2>/dev/null` - Check domain user
- **Line 283**: `groups "$domain_user" 2>/dev/null` - Get user groups

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_show_user.source.sh
- **Line 123**: `getent passwd "$username" 2>/dev/null` - Get user info
- **Line 142**: `getent passwd "$domain_format" 2>/dev/null` - Get domain user info
- **Line 170**: `getent group "$user_gid" 2>/dev/null` - Get group info
- **Line 184**: `getent shadow "$user_name" 2>/dev/null` - Get shadow info
- **Line 207**: `stat -c "%a" "$user_home" 2>/dev/null` - Get file permissions
- **Line 208**: `stat -c "%U" "$user_home" 2>/dev/null` - Get file owner
- **Line 223**: `command -v lastlog >/dev/null 2>&1` - Check lastlog availability
- **Line 224**: `lastlog -u "$user_name" 2>/dev/null` - Get last login
- **Line 233**: `command -v sudo >/dev/null 2>&1` - Check sudo availability
- **Line 234**: `sudo -l -U "$user_name" >/dev/null 2>&1` - Check sudo permissions
- **Line 243**: `ps -u "$user_name" --no-headers 2>/dev/null` - Get user processes
- **Line 248**: `command -v chage >/dev/null 2>&1` - Check chage availability
- **Line 250**: `sudo chage -l "$user_name" 2>/dev/null` - Get password info
- **Line 263**: `groups "$user_name" 2>/dev/null` - Get user groups
- **Line 274**: `getent group "$group" 2>/dev/null` - Get group info
- **Line 301**: `find /home /var /opt /usr/local -maxdepth 3 -user "$user_name" 2>/dev/null` - Find user files
- **Line 310**: `find /home /var /opt /usr/local -user "$user_name" 2>/dev/null` - Find all user files

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_list_users.source.sh
- **Line 176**: `getent passwd` - List all users
- **Line 206**: `getent shadow "$username" 2>/dev/null` - Get shadow info
- **Line 241**: `getent group "$gid" 2>/dev/null` - Get group info
- **Line 248**: `getent passwd` - List all users

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_set_path_permissions.source.sh
- **Line 209**: `stat -c "%a" "$reference_file" 2>/dev/null` - Get reference permissions
- **Line 244**: `stat -c "%a %A" "$path" 2>/dev/null` - Get current permissions
- **Line 255**: `stat -c "%U" "$path" 2>/dev/null` - Get file owner
- **Line 256**: `whoami 2>/dev/null` - Get current user
- **Line 288**: `stat -c "%a %A" "$path" 2>/dev/null` - Verify permissions
- **Line 295**: `find "$path" -print 2>/dev/null` - Count files
- **Line 339**: `find "$path" -type d -print0 2>/dev/null` - Find directories
- **Line 350**: `find "$path" -type f -print0 2>/dev/null` - Find files

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_set_path_owner.source.sh
- **Line 186**: `stat -c "%U:%G" "$reference_file" 2>/dev/null` - Get reference ownership
- **Line 210**: `getent passwd "$new_user" >/dev/null 2>&1` - Check user exists
- **Line 218**: `getent group "$new_group" >/dev/null 2>&1` - Check group exists
- **Line 268**: `stat -c "%U:%G" "$path" 2>/dev/null` - Verify ownership
- **Line 275**: `find "$path" -print 2>/dev/null` - Count files

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_show_acl_on_path.source.sh
- **Line 470**: `eval "$getfacl_cmd"` - Execute getfacl command

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_add_samba_user.source.sh
- **Line 102**: `getent passwd "$username" >/dev/null 2>&1` - Check user exists
- **Line 108**: `sudo pdbedit -L 2>/dev/null | grep -q "^$username:"` - Check Samba user exists
- **Line 151**: `sudo pdbedit -L 2>/dev/null | grep -q "^$username:"` - Verify Samba user

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_start_samba.source.sh
- **Line 83**: `systemctl is-active smbd >/dev/null 2>&1` - Check smbd status
- **Line 89**: `systemctl is-active nmbd >/dev/null 2>&1` - Check nmbd status

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_users_and_groups_inspect.source.sh
- **Line 9**: `getent passwd "$username" >/dev/null 2>&1` - Check user exists
- **Line 21**: `wbinfo --own-domain 2>/dev/null` - Get domain info
- **Line 31**: `sssctl domain-list 2>/dev/null` - List SSSD domains
- **Line 41**: `grep "^domains = " /etc/sssd/sssd.conf 2>/dev/null` - Read SSSD config
- **Line 51**: `grep "default_realm = " /etc/krb5.conf 2>/dev/null` - Read Kerberos config
- **Line 61**: `realm list 2>/dev/null` - List realms
- **Line 70**: `dnsdomainname 2>/dev/null` - Get DNS domain
- **Line 88**: `getent group "$groupname" >/dev/null 2>&1` - Check group exists
- **Line 106**: `wbinfo -t >/dev/null 2>&1` - Test domain trust
- **Line 123**: `systemctl is-active sssd >/dev/null 2>&1` - Check SSSD status
- **Line 167**: `wbinfo -i "$domain_user" >/dev/null 2>&1` - Get domain user info
- **Line 193**: `user_exists_in_passwd "$format"` - Check user in passwd
- **Line 240**: `groups "$user_identifier" 2>/dev/null` - Get user groups
- **Line 261**: `find /home /var /opt /usr/local -maxdepth 3 -user "$user_identifier" 2>/dev/null` - Find user files
- **Line 321**: `groups "$user_identifier" 2>/dev/null` - Get user groups
- **Line 356**: `groups "$user_identifier" 2>/dev/null` - Get user groups
- **Line 413**: `find /home /var /opt /usr/local -maxdepth 3 -user "$checkname" 2>/dev/null` - Find user files
- **Line 470**: `eval "$getfacl_cmd"` - Execute getfacl command

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_detect_firewall.source.sh
- **Line 85**: `command -v ufw >/dev/null 2>&1` - Check UFW availability
- **Line 89**: `ufw --version >/dev/null 2>&1` - Check UFW version
- **Line 90**: `ufw --version 2>/dev/null` - Get UFW version
- **Line 95**: `ufw status 2>/dev/null` - Get UFW status
- **Line 110**: `command -v firewall-cmd >/dev/null 2>&1` - Check firewalld availability
- **Line 114**: `firewall-cmd --version >/dev/null 2>&1` - Check firewalld version
- **Line 115**: `firewall-cmd --version 2>/dev/null` - Get firewalld version
- **Line 120**: `systemctl is-active firewalld >/dev/null 2>&1` - Check firewalld status
- **Line 137**: `command -v iptables >/dev/null 2>&1` - Check iptables availability
- **Line 142**: `iptables -L 2>/dev/null` - List iptables rules
- **Line 203**: `ufw status verbose 2>/dev/null` - Get UFW verbose status
- **Line 214**: `firewall-cmd --list-all 2>/dev/null` - List firewalld rules
- **Line 225**: `iptables -L -n --line-numbers 2>/dev/null` - List iptables rules

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_allow_samba_from.source.sh
- **Line 287**: `command -v iptables-save >/dev/null 2>&1` - Check iptables-save availability

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_list_samba_users.source.sh
- **Line 133**: `sudo pdbedit -v "$clean_username" 2>/dev/null` - Get Samba user details
- **Line 164**: `getent passwd "$clean_username" 2>/dev/null` - Get system user info
- **Line 193**: `sudo pdbedit -L 2>/dev/null` - List Samba users

---

## EXECUTE_OR_DRYRUN COMMANDS (With Dry-Run Support)

### /home/mathew/shuttle/scripts/2_post_install_config_steps/11_install_tools.sh
- **Line 87**: `sudo apt-get update` - Update package cache
- **Line 90**: `sudo dnf makecache` - Update package cache
- **Line 93**: `sudo yum makecache` - Update package cache
- **Line 133-142**: `sudo apt-get install -y $package_list` - Install packages

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_add_user.source.sh
- **Line 305-309**: `useradd` with various flags - Create system user
- **Line 318-322**: `echo '$username:$password' | chpasswd` - Set user password

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_add_group.source.sh
- **Line 98**: `groupadd` with various flags - Create system group

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_delete_user.source.sh
- **Line 169-173**: `cp -r '$user_home' '$backup_home'` - Backup user home
- **Line 204**: `userdel` with various flags - Delete user
- **Line 215-219**: `find /home /var /opt /usr/local -user '$username' -delete 2>/dev/null` - Delete user files
- **Line 272-276**: `cp -r '$user_home' '$backup_home'` - Backup domain user home
- **Line 298-301**: `rm -rf '$user_home'` - Remove user home
- **Line 307-311**: `find /home /var /opt /usr/local -user '$domain_user' -delete 2>/dev/null` - Delete domain user files

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_set_path_permissions.source.sh
- **Line 271**: `chmod '$mode' '$path'` - Set file permissions
- **Line 334**: `chmod '$dir_mode' '$dir'` - Set directory permissions
- **Line 344**: `chmod '$file_mode' '$file'` - Set file permissions

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_set_path_owner.source.sh
- **Line 260**: `chown '$ownership_string' '$path'` - Change file ownership

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_add_acl_to_path.source.sh
- **Line 518**: `setfacl --modify '$acl_entry' '$path'` - Add ACL entry

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_add_samba_user.source.sh
- **Line 135**: `printf '%s\n%s\n' "$password" "$password" | sudo smbpasswd -a -s "$username" >/dev/null 2>&1` - Add Samba user with password
- **Line 140**: `sudo smbpasswd -a "$username"` - Add Samba user
- **Line 145**: `sudo smbpasswd -e "$username" >/dev/null 2>&1` - Enable Samba user

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_start_samba.source.sh
- **Line 68**: `sudo systemctl start smbd` - Start Samba daemon
- **Line 73**: `sudo systemctl start nmbd` - Start NetBIOS daemon

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_users_and_groups_inspect.source.sh
- **Line 294**: `usermod -d '$home_dir' -m '$user_identifier'` - Move user home
- **Line 328**: `gpasswd -a '$user_identifier' '$groupname'` - Add user to group
- **Line 363**: `gpasswd -d '$user_identifier' '$groupname'` - Remove user from group
- **Line 518**: `setfacl --modify '$acl_entry' '$path'` - Modify ACL
- **Line 555**: `setfacl --remove '$acl_entry' '$path'` - Remove ACL

### /home/mathew/shuttle/scripts/2_post_install_config_steps/lib/_cmd_allow_samba_from.source.sh
- **Line 232**: `sudo ufw allow from $src to any port $port proto $proto$rule_comment` - Allow UFW rule
- **Line 255**: `sudo firewall-cmd --add-rich-rule="$rich_rule" --permanent` - Add firewalld rule
- **Line 261**: `sudo firewall-cmd --reload` - Reload firewalld
- **Line 281**: `sudo iptables -A INPUT -s $src -p $proto --dport $port $rule_comment -j ACCEPT` - Add iptables rule
- **Line 288**: `sudo iptables-save > /etc/iptables/rules.v4` - Save iptables rules

---

## EXECUTE COMMANDS (Read-Only Wrapper)

**No commands found using the `execute()` wrapper function.**

---

## ANALYSIS SUMMARY

### Command Categories by Function:
1. **System Information Gathering** (bare): `getent`, `stat`, `groups`, `whoami`, `ps`, `systemctl is-active`
2. **File System Operations** (bare): `find`, `grep`, most file reading operations
3. **Package Management Queries** (bare): `dpkg -l`, `rpm -q`, `command -v`
4. **Network/Domain Information** (bare): `wbinfo`, `sssctl`, `realm`, `dnsdomainname`
5. **System Modifications** (execute_or_dryrun): `useradd`, `groupadd`, `chmod`, `chown`, `systemctl start`
6. **Package Installation** (execute_or_dryrun): `apt-get install`, `dnf install`, `yum install`
7. **Service Management** (execute_or_dryrun): `systemctl start`, `smbpasswd`, firewall commands

### Security Pattern:
The scripts follow a secure pattern where:
- **Read-only operations** are executed directly (bare)
- **System-modifying operations** are wrapped with `execute_or_dryrun()` to support testing
- **All destructive operations** require explicit execution (not dry-run)
- **Sudo commands** are clearly identified and wrapped appropriately

### Recommendations:
1. Consider wrapping more bare read operations with `execute()` for consistency and logging
2. All system modification commands are properly wrapped with `execute_or_dryrun()`
3. The pattern is consistent and follows security best practices