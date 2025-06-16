# Global variables for detection results
DETECTED_DOMAIN=""
DETECTED_INTEGRATION=""
DETECTED_DOMAIN_USER_FORMAT=""

# Helper function to check if a user exists (using getent)
user_exists_in_passwd() {
    local username="$1"
    [[ -n "$username" ]] && getent passwd "$username" >/dev/null 2>&1
}


# Function to detect the domain this machine is joined to
# Sets DETECTED_DOMAIN global variable and returns 0 on success, 1 on failure
detect_machine_domain() {
    DETECTED_DOMAIN=""  # Clear global variable
    local detected_domain=""
    
    # Method 1: Check Winbind
    if check_command "wbinfo"; then
        detected_domain=$(wbinfo --own-domain 2>/dev/null | grep -v "^BUILTIN$" | head -1)
        if [[ -n "$detected_domain" ]]; then
            log INFO "Detected domain via Winbind: $detected_domain"
            DETECTED_DOMAIN="$detected_domain"
            return 0
        fi
    fi
    
    # Method 2: Check SSSD
    if check_command "sssctl"; then
        detected_domain=$(sssctl domain-list 2>/dev/null | head -1)
        if [[ -n "$detected_domain" ]]; then
            log INFO "Detected domain via SSSD: $detected_domain"
            DETECTED_DOMAIN="$detected_domain"
            return 0
        fi
    fi
    
    # Method 3: Parse SSSD config directly
    if [[ -r /etc/sssd/sssd.conf ]]; then
        detected_domain=$(grep "^domains = " /etc/sssd/sssd.conf 2>/dev/null | cut -d= -f2 | xargs | cut -d, -f1)
        if [[ -n "$detected_domain" ]]; then
            log INFO "Detected domain from SSSD config: $detected_domain"
            DETECTED_DOMAIN="$detected_domain"
            return 0
        fi
    fi
    
    # Method 4: Check Kerberos default realm
    if [[ -r /etc/krb5.conf ]]; then
        detected_domain=$(grep "default_realm = " /etc/krb5.conf 2>/dev/null | awk '{print $3}')
        if [[ -n "$detected_domain" ]]; then
            log INFO "Detected domain from Kerberos: $detected_domain"
            DETECTED_DOMAIN="$detected_domain"
            return 0
        fi
    fi
    
    # Method 5: Check realm list
    if check_command "realm"; then
        detected_domain=$(realm list 2>/dev/null | grep "domain-name:" | head -1 | awk '{print $2}')
        if [[ -n "$detected_domain" ]]; then
            log INFO "Detected domain via realm: $detected_domain"
            DETECTED_DOMAIN="$detected_domain"
            return 0
        fi
    fi
    
    # Method 6: DNS domain name
    detected_domain=$(dnsdomainname 2>/dev/null)
    if [[ -n "$detected_domain" && "$detected_domain" != "(none)" ]]; then
        log INFO "Detected domain from DNS: $detected_domain"
        DETECTED_DOMAIN="$detected_domain"
        return 0
    fi
    
    log WARN "Could not detect domain membership"
    return 1
}



# Function to check if a group exists
# Returns 0 if group exists, 1 if not
# Usage: group_exists "groupname"
group_exists() {
    local groupname="$1"
    [[ -n "$groupname" ]] && getent group "$groupname" >/dev/null 2>&1
}






# Function to test Winbind connectivity
# Returns 0 if Winbind is working, 1 if not, 2 if not available
# Usage: verify_winbind_connectivity
verify_winbind_connectivity() {
    # Check if wbinfo command exists
    if ! check_command "wbinfo"; then
        return 2
    fi
    
    # Test domain trust
    if wbinfo -t >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Function to test SSSD connectivity
# Returns 0 if SSSD is working, 1 if not, 2 if not available
# Usage: verify_sssd_connectivity
verify_sssd_connectivity() {
    # Check if sss_cache command exists
    if ! check_command "sss_cache"; then
        return 2
    fi
    
    # Check if sssd service is running
    if systemctl is-active sssd >/dev/null 2>&1; then
        return 0
    fi
    
    return 1
}

# Function to detect domain integration method
# Sets DETECTED_INTEGRATION global variable to "winbind", "sssd", or "none"
# Returns 0 if integration found, 1 if none
detect_domain_integration() {
    DETECTED_INTEGRATION=""  # Clear global variable
    log INFO "Detecting domain integration method..."

    if check_command "wbinfo" && verify_winbind_connectivity; then
        DETECTED_INTEGRATION="winbind"
        log INFO "Detected winbind integration: $DETECTED_INTEGRATION"
        return 0
    fi
    
    if check_command "sss_cache" && verify_sssd_connectivity; then
        DETECTED_INTEGRATION="sssd"
        log INFO "Detected sssd integration: $DETECTED_INTEGRATION"
        return 0
    fi
    
    DETECTED_INTEGRATION="none"
    log WARN "Detected no domain integration: $DETECTED_INTEGRATION"
    return 1
}

# Function to verify domain user exists via Winbind
# Returns 0 if user found in domain, 1 if not found
# Usage: verify_domain_user_winbind "DOMAIN\\username"
verify_domain_user_winbind() {
    local domain_user="$1"
    
    # Check if wbinfo command is available
    if ! check_command "wbinfo"; then
        log DEBUG "wbinfo command not available for domain user verification"
        return 1
    fi
    
    # For Winbind, check if user exists in domain using wbinfo
    if wbinfo -i "$domain_user" >/dev/null 2>&1; then
        log DEBUG "Found domain user via wbinfo: $domain_user"
        return 0
    else
        log DEBUG "Domain user not found via wbinfo: $domain_user"
        return 1
    fi
}

# Function to check if a domain user already has local resources
# Returns 0 if user has local resources, 1 if not
# Sets DETECTED_DOMAIN_USER_FORMAT global variable to the format that worked
check_domain_user_exists_locally_in_passwd() {
    local username="$1"
    local domain="$2"
    DETECTED_DOMAIN_USER_FORMAT=""  # Clear global variable
    log DEBUG "Searching for user resources for $username in $domain on local machine"
    local possible_formats=(
        "${domain}\\${username}"
        "${domain}+${username}"
        "${username}@${domain}"
        "${username}"  # Some setups use just username for default domain
    )
    
    for format in "${possible_formats[@]}"; do
        log DEBUG "Checking domain user format in passwd: $format"
        if user_exists_in_passwd "$format"; then
            DETECTED_DOMAIN_USER_FORMAT="$format"  # Set the format that worked
            log DEBUG "Found domain user in passwd: $format"
            return 0  # Found locally
        else
            log DEBUG "Domain user format not found in passwd: $format"
        fi
    done
    
    return 1  # Not found locally
}

# Function to check for existing home directories for a user
# Returns 0 if home directories found, 1 if none found
# Usage: check_user_home_directories "username" "custom_home_path"
check_user_home_directories() {
    local username="$1"
    local custom_home="${2:-}"
    local found_homes=()
    
    # Check default home directory
    local default_home="/home/$username"
    if [[ -d "$default_home" ]]; then
        found_homes+=("$default_home")
        log DEBUG "Found existing default home directory: $default_home"
    fi
    
    # Check custom home directory if different from default
    if [[ -n "$custom_home" && "$custom_home" != "$default_home" && -d "$custom_home" ]]; then
        found_homes+=("$custom_home")
        log DEBUG "Found existing custom home directory: $custom_home"
    fi
    
    if [[ ${#found_homes[@]} -gt 0 ]]; then
        return 0  # Found home directories
    else
        return 1  # No home directories found
    fi
}

# Function to check for existing group memberships for a user
# Returns 0 if user has group memberships, 1 if none found
# Usage: check_user_group_memberships "username_or_domain_user"
check_user_group_memberships() {
    local user_identifier="$1"
    
    local user_groups=""
    if user_groups=$(groups "$user_identifier" 2>/dev/null); then
        # Extract just the group names (groups command output: "username : group1 group2 group3")
        local group_list=$(echo "$user_groups" | cut -d: -f2 | xargs)
        if [[ -n "$group_list" ]]; then
            log DEBUG "Found existing group memberships for '$user_identifier': $group_list"
            return 0  # Has group memberships
        fi
    fi
    
    log DEBUG "No group memberships found for '$user_identifier'"
    return 1  # No group memberships
}

# Function to check for files owned by a user
# Returns 0 if files found, 1 if none found  
# Usage: check_user_owned_files "username_or_domain_user"
check_user_owned_files() {
    local user_identifier="$1"
    
    # Look for files owned by the user in common locations
    local owned_files=""
    if owned_files=$(find /home /var /opt /usr/local -maxdepth 3 -user "$user_identifier" 2>/dev/null | head -5); then
        if [[ -n "$owned_files" ]]; then
            local file_count=$(echo "$owned_files" | wc -l)
            log DEBUG "Found $file_count files owned by '$user_identifier' (showing first 5): $owned_files"
            return 0  # Found owned files
        fi
    fi
    
    log DEBUG "No files found owned by '$user_identifier'"
    return 1  # No owned files found
}

# Function to modify/create and configure a home directory for a user (local or domain)
# Returns 0 on success, 1 on failure
# Usage: modify_user_home_directory "username" "domain_user_or_empty" "home_dir_path"
modify_user_home_directory() {
    local username="$1"
    local domain_user="${2:-}"  # Optional - empty for local users
    local home_dir="${3:-}"
    
    # Determine which user identifier to use
    local user_identifier="${domain_user:-$username}"
    
    # Set default home directory if not provided
    if [[ -z "$home_dir" ]]; then
        home_dir="/home/$username"
        log INFO "Using default home directory: $home_dir"
    fi
    
    # Use usermod to set/move home directory
    log INFO "Setting home directory for '$user_identifier' to '$home_dir'"
    local usermod_cmd="usermod -d '$home_dir' -m '$user_identifier'"
    if ! check_active_user_is_root; then
        usermod_cmd="sudo $usermod_cmd"
    fi
    
    # Execute usermod - it will handle creation, permissions, and ownership
    execute_or_dryrun "$usermod_cmd" "Set home directory for '$user_identifier'" "Failed to set home directory for '$user_identifier'" || return 1
    
    return 0
}

# Function to add a user to a group (works for both local and domain users)
# Returns 0 on success, 1 on failure
# Usage: add_user_to_group_core "username" "domain_user_or_empty" "groupname"
add_user_to_group_core() {
    local username="$1"
    local domain_user="${2:-}"  # Optional - empty for local users
    local groupname="$3"
    
    # Determine which user identifier to use
    local user_identifier="${domain_user:-$username}"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        log ERROR "Group '$groupname' does not exist"
        return 1
    fi
    
    # Check if user is already in the group
    if groups "$user_identifier" 2>/dev/null | grep -q "\b$groupname\b"; then
        log INFO "User '$user_identifier' is already a member of group '$groupname'"
        return 0
    fi
    
    # Add user to group using gpasswd
    log INFO "Adding user '$user_identifier' to group '$groupname'"
    local gpasswd_cmd="gpasswd -a '$user_identifier' '$groupname'"
    if ! check_active_user_is_root; then
        gpasswd_cmd="sudo $gpasswd_cmd"
    fi
    
    execute_or_dryrun "$gpasswd_cmd" "Added '$user_identifier' to group '$groupname'" "Failed to add '$user_identifier' to group '$groupname'" || return 1
    
    return 0
}

# Function to remove a user from a group (works for both local and domain users)
# Returns 0 on success, 1 on failure
# Usage: remove_user_from_group_core "username" "domain_user_or_empty" "groupname"
remove_user_from_group_core() {
    local username="$1"
    local domain_user="${2:-}"  # Optional - empty for local users
    local groupname="$3"
    
    # Determine which user identifier to use
    local user_identifier="${domain_user:-$username}"
    
    # Check if group exists
    if ! group_exists "$groupname"; then
        log ERROR "Group '$groupname' does not exist"
        return 1
    fi
    
    # Check if user is in the group
    if ! groups "$user_identifier" 2>/dev/null | grep -q "\b$groupname\b"; then
        log INFO "User '$user_identifier' is not a member of group '$groupname'"
        return 0
    fi
    
    # Remove user from group using gpasswd
    log INFO "Removing user '$user_identifier' from group '$groupname'"
    local gpasswd_cmd="gpasswd -d '$user_identifier' '$groupname'"
    if ! check_active_user_is_root; then
        gpasswd_cmd="sudo $gpasswd_cmd"
    fi
    
    execute_or_dryrun "$gpasswd_cmd" "Removed '$user_identifier' from group '$groupname'" "Failed to remove '$user_identifier' from group '$groupname'" || return 1
    
    return 0
}

# Function to comprehensively check for any local resources for a user (local or domain)
# Returns 0 if any resources found, 1 if clean
# Populates global array DETECTED_USER_RESOURCES with found issues
# Usage: check_user_all_local_resources "username" "domain_user_or_empty" "custom_home_path"
declare -a DETECTED_USER_RESOURCES
check_user_all_local_resources() {
    local username="$1"
    local domain_user="${2:-}"
    local custom_home="${3:-}"
    
    DETECTED_USER_RESOURCES=()  # Clear global array
    local has_resources=false
    
    # Determine which user identifier to use for checks
    local checkname="${domain_user:-$username}"
    
    log DEBUG "Checking all local resources for user '$checkname'..."
    
    # Check home directories
    if check_user_home_directories "$username" "$custom_home"; then
        has_resources=true
        local default_home="/home/$username"
        if [[ -d "$default_home" ]]; then
            DETECTED_USER_RESOURCES+=("Home directory exists: $default_home")
        fi
        if [[ -n "$custom_home" && "$custom_home" != "$default_home" && -d "$custom_home" ]]; then
            DETECTED_USER_RESOURCES+=("Custom home directory exists: $custom_home")
        fi
    fi
    
    # Check group memberships
    if check_user_group_memberships "$checkname"; then
        has_resources=true
        local user_groups=$(groups "$checkname" 2>/dev/null | cut -d: -f2 | xargs)
        DETECTED_USER_RESOURCES+=("Local group memberships: $user_groups")
    fi
    
    # Check owned files
    if check_user_owned_files "$checkname"; then
        has_resources=true
        local owned_files=$(find /home /var /opt /usr/local -maxdepth 3 -user "$checkname" 2>/dev/null | head -5 | tr '\n' ' ')
        DETECTED_USER_RESOURCES+=("Files owned by user (showing first 5): $owned_files")
    fi
    
    if [[ "$has_resources" == "true" ]]; then
        log DEBUG "Found ${#DETECTED_USER_RESOURCES[@]} types of local resources for '$checkname'"
        return 0  # Resources found
    else
        log DEBUG "No local resources found for '$checkname'"
        return 1  # No resources found
    fi
}

# Function to show ACLs for a path (works for files and directories)
# Returns 0 on success, 1 on failure
# Usage: show_acl_on_path_core "path" "recursive" "effective" "numeric" "show_default"
show_acl_on_path_core() {
    local path="$1"
    local recursive="$2"
    local effective="$3"
    local numeric="$4"
    local show_default="$5"
    
    # Build getfacl command
    local getfacl_cmd="getfacl"
    
    # Add flags based on options
    if [[ "$recursive" == "true" ]]; then
        getfacl_cmd="$getfacl_cmd --recursive"
    fi
    
    if [[ "$effective" == "true" ]]; then
        getfacl_cmd="$getfacl_cmd --access"
    fi
    
    if [[ "$numeric" == "true" ]]; then
        getfacl_cmd="$getfacl_cmd --numeric"
    fi
    
    if [[ "$show_default" == "true" ]]; then
        if [[ -d "$path" ]]; then
            getfacl_cmd="$getfacl_cmd --default"
        else
            log WARN "Default ACLs only apply to directories, ignoring --default for file: $path"
        fi
    fi
    
    # Add the path (quote it for safety)
    getfacl_cmd="$getfacl_cmd '$path'"
    
    log INFO "Showing ACLs for: $path"
    
    # Execute getfacl command
    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would execute: $getfacl_cmd"
    else
        log DEBUG "Executing: $getfacl_cmd"
        if eval "$getfacl_cmd"; then
            log DEBUG "Successfully displayed ACLs for: $path"
        else
            log ERROR "Failed to display ACLs for: $path"
            return 1
        fi
    fi
    
    return 0
}

# Function to add an ACL entry to a path (files and directories)
# Returns 0 on success, 1 on failure
# Usage: add_acl_to_path_core "path" "acl_entry" "recursive" "default_acl"
add_acl_to_path_core() {
    local path="$1"
    local acl_entry="$2"
    local recursive="$3"
    local default_acl="$4"
    
    # Build setfacl command
    local setfacl_cmd="setfacl"
    
    # Add sudo if not root
    if ! check_active_user_is_root; then
        setfacl_cmd="sudo $setfacl_cmd"
    fi
    
    # Add flags based on options
    if [[ "$recursive" == "true" ]]; then
        setfacl_cmd="$setfacl_cmd --recursive"
    fi
    
    if [[ "$default_acl" == "true" ]]; then
        if [[ -d "$path" ]]; then
            setfacl_cmd="$setfacl_cmd --default"
        else
            log ERROR "Default ACLs only apply to directories, cannot set default ACL for file: $path"
            return 1
        fi
    fi
    
    # Add modify flag and ACL entry (quote for safety)
    setfacl_cmd="$setfacl_cmd --modify '$acl_entry' '$path'"
    
    log INFO "Adding ACL '$acl_entry' to: $path"
    
    # Execute setfacl command
    execute_or_dryrun "$setfacl_cmd" "Added ACL '$acl_entry' to '$path'" "Failed to add ACL '$acl_entry' to '$path'" || return 1
    
    return 0
}

# Function to remove an ACL entry from a path (files and directories)
# Returns 0 on success, 1 on failure
# Usage: remove_acl_from_path_core "path" "acl_entry" "recursive" "default_acl"
remove_acl_from_path_core() {
    local path="$1"
    local acl_entry="$2"
    local recursive="$3"
    local default_acl="$4"
    
    # Build setfacl command
    local setfacl_cmd="setfacl"
    
    # Add sudo if not root
    if ! check_active_user_is_root; then
        setfacl_cmd="sudo $setfacl_cmd"
    fi
    
    # Add flags based on options
    if [[ "$recursive" == "true" ]]; then
        setfacl_cmd="$setfacl_cmd --recursive"
    fi
    
    if [[ "$default_acl" == "true" ]]; then
        if [[ -d "$path" ]]; then
            setfacl_cmd="$setfacl_cmd --default"
        else
            log ERROR "Default ACLs only apply to directories, cannot remove default ACL from file: $path"
            return 1
        fi
    fi
    
    # Add remove flag and ACL entry (quote for safety)
    setfacl_cmd="$setfacl_cmd --remove '$acl_entry' '$path'"
    
    log INFO "Removing ACL '$acl_entry' from: $path"
    
    # Execute setfacl command
    execute_or_dryrun "$setfacl_cmd" "Removed ACL '$acl_entry' from '$path'" "Failed to remove ACL '$acl_entry' from '$path'" || return 1
    
    return 0
}