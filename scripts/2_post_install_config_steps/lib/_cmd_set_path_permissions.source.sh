# Input validation library will be loaded by the main script's setup lib loader

# Command-specific help functions
show_help_set_path_permissions() {
    cat << EOF
Usage: $SCRIPT_NAME set-path-permissions --path <path> --mode <permissions> [options]

Change permissions of files and directories using chmod.

Required Parameters:
  --path <path>         Path to change permissions for
  --mode <permissions>  Permission mode (octal, symbolic, or special formats)

Optional Parameters:
  --recursive           Apply changes recursively to directories
  --file-mode <perms>   Permissions for files when using --recursive
  --dir-mode <perms>    Permissions for directories when using --recursive
  --preserve-root       Prevent changes to root directory (/)
  --reference <file>    Copy permissions from reference file
  --dry-run             Show what would be done without making changes

Permission Formats:
  Octal:    755, 644, 600, 777, etc.
  Symbolic: u+rwx, g+r, o-w, a=rx, etc.
  Special:  +x (add execute), -w (remove write), =r (set read only)

Common Permission Examples:
  755  = rwxr-xr-x  (executable file, readable by all)
  644  = rw-r--r--  (regular file, writable by owner only)
  600  = rw-------  (private file, owner only)
  777  = rwxrwxrwx  (full permissions for all - rarely recommended)
  
Symbolic Examples:
  u+x     Add execute for user (owner)
  g+w     Add write for group  
  o-r     Remove read for others
  a+r     Add read for all (user, group, others)
  u=rwx   Set user permissions to read, write, execute
  go=r    Set group and others to read only

Examples:
  # Set octal permissions
  $SCRIPT_NAME set-path-permissions --path /home/user/script.sh --mode 755
  
  # Add execute permission for everyone
  $SCRIPT_NAME set-path-permissions --path /usr/local/bin/tool --mode +x
  
  # Remove write permission for group and others
  $SCRIPT_NAME set-path-permissions --path /etc/config --mode go-w
  
  # Set permissions recursively
  $SCRIPT_NAME set-path-permissions --path /var/www --mode 755 --recursive
  
  # Copy permissions from reference file
  $SCRIPT_NAME set-path-permissions --path /new/file --reference /existing/file
  
  # Make file private (owner only)
  $SCRIPT_NAME set-path-permissions --path /home/user/private.txt --mode 600

Notes:
  - Requires appropriate permissions (usually owner or root/sudo)
  - Octal format: user-group-other (e.g., 755 = rwxr-xr-x)
  - Symbolic format allows precise control over specific permission bits
  - --preserve-root prevents accidental changes to system root
  - Be careful with recursive permission changes on system directories
EOF
}

cmd_set_path_permissions() {
    # Capture original parameters before they're consumed by parsing
    local original_params="$*"
    
    local path=""
    local mode=""
    local recursive=false
    local file_mode=""
    local dir_mode=""
    local preserve_root=true
    local reference_file=""
    
    # Parse parameters
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --path)
                path=$(validate_parameter_value "$1" "${2:-}" "Path required after --path" "show_help_set_path_permissions")
                shift 2
                ;;
            --mode)
                mode=$(validate_parameter_value "$1" "${2:-}" "Permission mode required after --mode" "show_help_set_path_permissions")
                shift 2
                ;;
            --recursive)
                recursive=true
                shift
                ;;
            --file-mode)
                file_mode=$(validate_parameter_value "$1" "${2:-}" "File permission mode required after --file-mode" "show_help_set_path_permissions")
                shift 2
                ;;
            --dir-mode)
                dir_mode=$(validate_parameter_value "$1" "${2:-}" "Directory permission mode required after --dir-mode" "show_help_set_path_permissions")
                shift 2
                ;;
            --preserve-root)
                preserve_root=true
                shift
                ;;
            --no-preserve-root)
                preserve_root=false
                shift
                ;;
            --reference)
                reference_file=$(validate_parameter_value "$1" "${2:-}" "Reference file required after --reference" "show_help_set_path_permissions")
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help_set_path_permissions
                return 0
                ;;
            *)
                show_help_set_path_permissions
                error_exit "Unknown parameter: $1"
                ;;
        esac
    done
    
    # Validate required parameters
    if [[ -z "$path" ]]; then
        show_help_set_path_permissions
        error_exit "Path is required"
    fi
    
    # Validate permission specification
    if [[ -z "$mode" && -z "$reference_file" && -z "$file_mode" && -z "$dir_mode" ]]; then
        show_help_set_path_permissions
        error_exit "Must specify either --mode, --reference, or both --file-mode and --dir-mode"
    fi
    
    # Validate conflicting options
    if [[ -n "$mode" && -n "$reference_file" ]]; then
        show_help_set_path_permissions
        error_exit "Cannot specify both --mode and --reference options"
    fi
    
    # Validate file-mode/dir-mode usage
    if [[ (-n "$file_mode" || -n "$dir_mode") && -n "$mode" ]]; then
        show_help_set_path_permissions
        error_exit "Cannot specify both --mode and --file-mode/--dir-mode options"
    fi
    
    if [[ (-n "$file_mode" || -n "$dir_mode") && -n "$reference_file" ]]; then
        show_help_set_path_permissions
        error_exit "Cannot specify both --reference and --file-mode/--dir-mode options"
    fi
    
    # If using separate file/dir modes, recursive must be enabled and both modes must be specified
    if [[ -n "$file_mode" || -n "$dir_mode" ]]; then
        if [[ "$recursive" != "true" ]]; then
            show_help_set_path_permissions
            error_exit "--file-mode and --dir-mode require --recursive option"
        fi
        if [[ -z "$file_mode" || -z "$dir_mode" ]]; then
            show_help_set_path_permissions
            error_exit "Both --file-mode and --dir-mode must be specified when using separate permissions"
        fi
    fi
    
    log_command_call "set-path-permissions" "$original_params"
    
    # Input validation for security
    if ! validate_input "path" "$path" "path"; then
        error_exit "Invalid path provided to set path permissions function"
    fi
    
    # Validate permission modes if provided
    if [[ -n "$mode" ]]; then
        if ! validate_input "mode" "$mode" "permission mode"; then
            error_exit "Invalid permission mode provided"
        fi
    fi
    
    if [[ -n "$file_mode" ]]; then
        if ! validate_input "mode" "$file_mode" "file mode"; then
            error_exit "Invalid file mode provided"
        fi
    fi
    
    if [[ -n "$dir_mode" ]]; then
        if ! validate_input "mode" "$dir_mode" "directory mode"; then
            error_exit "Invalid directory mode provided"
        fi
    fi
    
    # Validate reference file if provided
    if [[ -n "$reference_file" ]]; then
        if ! validate_input "path" "$reference_file" "reference file"; then
            error_exit "Invalid reference file path provided"
        fi
    fi
    
    # Check tool availability
    check_tool_permission_or_error_exit "chmod" "change permissions" "chmod not available - cannot change file permissions"
    
    # Validate path exists (with sudo fallback for permission-restricted paths)
    if ! check_path_exists_with_sudo "$path" "true" "true"; then
        error_exit "Path does not exist: $path"
    fi
    
    # Protect root directory
    if [[ "$preserve_root" == "true" && "$path" == "/" ]]; then
        error_exit "Refusing to change permissions of root directory (/). Use --no-preserve-root if you really want this"
    fi
    
    # Call the core function
    set_path_permissions_core "$path" "$mode" "$recursive" "$reference_file" "$file_mode" "$dir_mode"
    
    return 0
}

# Core function to set path permissions
set_path_permissions_core() {
    local path="$1"
    local mode="$2"
    local recursive="$3"
    local reference_file="$4"
    local file_mode="$5"
    local dir_mode="$6"
    
    # Handle reference file
    if [[ -n "$reference_file" ]]; then
        if ! check_path_exists_with_sudo "$reference_file" "true" "true"; then
            log ERROR "Reference file does not exist: $reference_file"
            return 1
        fi
        
        # Get permissions from reference file
        local ref_permissions=""
        if ! ref_permissions=$(stat -c "%a" "$reference_file" 2>/dev/null); then
            log ERROR "Could not get permission information from reference file: $reference_file"
            return 1
        fi
        
        mode="$ref_permissions"
        log INFO "Using permissions from reference file '$reference_file': $mode"
    fi
    
    # Check if we're using separate file/directory modes
    if [[ -n "$file_mode" && -n "$dir_mode" ]]; then
        # Validate both permission modes
        if ! validate_permission_mode "$file_mode"; then
            log ERROR "Invalid file permission mode: $file_mode"
            return 1
        fi
        if ! validate_permission_mode "$dir_mode"; then
            log ERROR "Invalid directory permission mode: $dir_mode"
            return 1
        fi
        
        log INFO "Using separate permissions - Files: $file_mode, Directories: $dir_mode"
        set_separate_file_dir_permissions "$path" "$file_mode" "$dir_mode"
        return $?
    else
        # Original single-mode logic
        # Validate permission mode format
        if ! validate_permission_mode "$mode"; then
            log ERROR "Invalid permission mode: $mode"
            log ERROR "Valid formats: octal (755), symbolic (u+x,g-w), or special (+x,-w,=r)"
            return 1
        fi
        
        # Show current permissions for reference
        local current_permissions=""
        if current_permissions=$(stat -c "%a %A" "$path" 2>/dev/null); then
            log INFO "Current permissions of '$path': $current_permissions"
        fi
        
        # Build chmod command
        local chmod_cmd="chmod"
        
        # Add sudo if not root and we don't own the file
        if ! check_active_user_is_root; then
            local file_owner=""
            local current_user=""
            if file_owner=$(stat -c "%U" "$path" 2>/dev/null) && current_user=$(whoami 2>/dev/null); then
                if [[ "$file_owner" != "$current_user" ]]; then
                    chmod_cmd="sudo $chmod_cmd"
                fi
            else
                # If we can't determine ownership, assume we need sudo
                chmod_cmd="sudo $chmod_cmd"
            fi
        fi
        
        # Add flags
        if [[ "$recursive" == "true" ]]; then
            chmod_cmd="$chmod_cmd --recursive"
        fi
        
        # Add mode and path
        chmod_cmd="$chmod_cmd '$mode' '$path'"
        
        # Show what will be changed
        log INFO "Changing permissions of '$path' to '$mode'"
        if [[ "$recursive" == "true" ]]; then
            log INFO "Applying changes recursively"
        fi
        
        # Safety check before executing chmod command
        if ! check_path_safety "$path" "change permissions"; then
            return 1
        fi
        
        # Execute chmod command
        execute_or_dryrun "$chmod_cmd" "Changed permissions of '$path' to '$mode'" "Failed to change permissions of '$path'" \
                         "Modify file or directory permissions to control access (read/write/execute) for owner/group/others" || return 1
        
        # Show summary of changes if not dry run
        if [[ "$DRY_RUN" != "true" ]]; then
            log INFO "Permission change completed successfully"
            
            # Show new permissions for verification
            local new_permissions=""
            if new_permissions=$(stat -c "%a %A" "$path" 2>/dev/null); then
                log INFO "New permissions of '$path': $new_permissions"
            fi
            
            # For recursive changes, show count of affected files
            if [[ "$recursive" == "true" && -d "$path" ]]; then
                local file_count=0
                if file_count=$(find "$path" -print 2>/dev/null | wc -l); then
                    log INFO "Total files/directories processed: $file_count"
                fi
            fi
            
            # Show interpretation of octal permissions if used
            if [[ "$mode" =~ ^[0-7]{3,4}$ ]]; then
                interpret_octal_permissions "$mode"
            fi
        fi
    fi
    
    return 0
}

# Function to apply directory permissions using batch operations
apply_dir_permissions() {
    local path="$1"
    local dir_mode="$2"
    
    local dirs_found=0
    local dirs_processed=0
    
    # Count directories first for progress tracking
    if [[ "$VERBOSE" == "true" ]]; then
        if dirs_found=$(find "$path" -type d 2>/dev/null | wc -l); then
            log INFO "Found $dirs_found directories to process"
        fi
    fi
    
    # Use find with -exec + for batch processing (more efficient than individual chmod calls)
    if find "$path" -type d -exec chmod "$dir_mode" {} + 2>/dev/null; then
        # Count successful operations for reporting
        if dirs_processed=$(find "$path" -type d 2>/dev/null | wc -l); then
            log INFO "Successfully set directory permissions ($dir_mode) on $dirs_processed directories"
            if [[ "$VERBOSE" == "true" ]]; then
                # Show some examples of what was processed
                log INFO "Sample directories processed:"
                find "$path" -type d 2>/dev/null | head -5 | while read -r dir; do
                    log INFO "  $dir -> $dir_mode"
                done
                if [[ $dirs_processed -gt 5 ]]; then
                    log INFO "  ... and $((dirs_processed - 5)) more directories"
                fi
            fi
        fi
        return 0
    else
        log ERROR "Failed to set directory permissions using batch operation"
        return 1
    fi
}

# Function to apply file permissions using batch operations
apply_file_permissions() {
    local path="$1"
    local file_mode="$2"
    
    local files_found=0
    local files_processed=0
    
    # Count files first for progress tracking
    if [[ "$VERBOSE" == "true" ]]; then
        if files_found=$(find "$path" -type f 2>/dev/null | wc -l); then
            log INFO "Found $files_found files to process"
        fi
    fi
    
    # Use find with -exec + for batch processing (more efficient than individual chmod calls)
    if find "$path" -type f -exec chmod "$file_mode" {} + 2>/dev/null; then
        # Count successful operations for reporting
        if files_processed=$(find "$path" -type f 2>/dev/null | wc -l); then
            log INFO "Successfully set file permissions ($file_mode) on $files_processed files"
            if [[ "$VERBOSE" == "true" ]]; then
                # Show some examples of what was processed
                log INFO "Sample files processed:"
                find "$path" -type f 2>/dev/null | head -5 | while read -r file; do
                    log INFO "  $file -> $file_mode"
                done
                if [[ $files_processed -gt 5 ]]; then
                    log INFO "  ... and $((files_processed - 5)) more files"
                fi
            fi
        fi
        return 0
    else
        log ERROR "Failed to set file permissions using batch operation"
        return 1
    fi
}

# Function to set separate permissions for files and directories
set_separate_file_dir_permissions() {
    local path="$1"
    local file_mode="$2"
    local dir_mode="$3"
    
    log INFO "Setting separate permissions recursively in '$path'"
    log INFO "  Files will be set to: $file_mode"
    log INFO "  Directories will be set to: $dir_mode"
    
    # Safety check before processing
    if ! check_path_safety "$path" "change permissions recursively"; then
        return 1
    fi
    
    local overall_success=true
    
    # First set permissions on directories using batch operations
    log INFO "Processing directory permissions..."
    if ! execute_function_or_dryrun_auto_sudo apply_dir_permissions \
        "Directory permissions applied successfully" \
        "Failed to apply directory permissions" \
        "Apply directory permissions ($dir_mode) to all directories in $path" \
        "$path" "$dir_mode"; then
        log ERROR "Directory permission application failed"
        overall_success=false
    fi
    
    # Then set permissions on files using batch operations
    log INFO "Processing file permissions..."
    if ! execute_function_or_dryrun_auto_sudo apply_file_permissions \
        "File permissions applied successfully" \
        "Failed to apply file permissions" \
        "Apply file permissions ($file_mode) to all files in $path" \
        "$path" "$file_mode"; then
        log ERROR "File permission application failed"
        overall_success=false
    fi
    
    # Show summary and permission interpretations
    if [[ "$overall_success" == "true" ]]; then
        log INFO "All permission changes completed successfully"
        
        # Show permission interpretations for octal modes
        if [[ "$file_mode" =~ ^[0-7]{3,4}$ ]]; then
            log INFO "File permission interpretation:"
            interpret_octal_permissions "$file_mode"
        fi
        
        if [[ "$dir_mode" =~ ^[0-7]{3,4}$ ]]; then
            log INFO "Directory permission interpretation:"
            interpret_octal_permissions "$dir_mode"
        fi
        
        return 0
    else
        log ERROR "Some permission changes failed"
        return 1
    fi
}

# Function to validate permission mode format
validate_permission_mode() {
    local mode="$1"
    
    # Check for valid formats:
    # Octal: 644, 755, 0755, etc.
    if [[ "$mode" =~ ^[0-7]{3,4}$ ]]; then
        return 0
    fi
    
    # Symbolic: u+rwx, g-w, o=r, a+x, etc.
    # Basic pattern matching for symbolic modes
    if [[ "$mode" =~ ^[ugoa]*[+=-][rwxXst]*$ ]] || \
       [[ "$mode" =~ ^[ugoa]*[+=-][rwxXst]*,[ugoa]*[+=-][rwxXst]*$ ]] || \
       [[ "$mode" =~ ^[+=-][rwxXst]*$ ]]; then
        return 0
    fi
    
    # Special shorthand formats: +x, -w, =r, etc.
    if [[ "$mode" =~ ^[+=-][rwxXst]+$ ]]; then
        return 0
    fi
    
    return 1
}

# Function to interpret octal permissions
interpret_octal_permissions() {
    local octal="$1"
    
    # Remove leading zeros for interpretation
    octal="${octal#0}"
    
    # Handle 3 or 4 digit octal
    local special=""
    local user=""
    local group=""
    local other=""
    
    if [[ ${#octal} -eq 4 ]]; then
        special="${octal:0:1}"
        user="${octal:1:1}"
        group="${octal:2:1}"
        other="${octal:3:1}"
    else
        user="${octal:0:1}"
        group="${octal:1:1}"
        other="${octal:2:1}"
    fi
    
    # Convert digits to rwx format
    local user_perms=$(octal_to_rwx "$user")
    local group_perms=$(octal_to_rwx "$group")
    local other_perms=$(octal_to_rwx "$other")
    
    log INFO "Permission interpretation: $user_perms$group_perms$other_perms"
    log INFO "  User (owner): $user_perms"
    log INFO "  Group:        $group_perms"
    log INFO "  Others:       $other_perms"
    
    # Interpret special permissions if present
    if [[ -n "$special" && "$special" != "0" ]]; then
        local special_desc=""
        case "$special" in
            1) special_desc="sticky bit" ;;
            2) special_desc="setgid" ;;
            3) special_desc="setgid + sticky bit" ;;
            4) special_desc="setuid" ;;
            5) special_desc="setuid + sticky bit" ;;
            6) special_desc="setuid + setgid" ;;
            7) special_desc="setuid + setgid + sticky bit" ;;
        esac
        log INFO "  Special:      $special_desc"
    fi
}

# Helper function to convert octal digit to rwx format
octal_to_rwx() {
    local digit="$1"
    
    case "$digit" in
        0) echo "---" ;;
        1) echo "--x" ;;
        2) echo "-w-" ;;
        3) echo "-wx" ;;
        4) echo "r--" ;;
        5) echo "r-x" ;;
        6) echo "rw-" ;;
        7) echo "rwx" ;;
        *) echo "???" ;;
    esac
}


# Function to suggest common permission patterns
suggest_permission_patterns() {
    cat << EOF

Common Permission Patterns:
  644 (rw-r--r--)  Regular files (readable by all, writable by owner)
  755 (rwxr-xr-x)  Executable files and directories
  600 (rw-------)  Private files (owner only)
  700 (rwx------)  Private directories (owner only)
  664 (rw-rw-r--)  Group-writable files
  775 (rwxrwxr-x)  Group-writable directories
  
Security Considerations:
  - Avoid 777 permissions (world-writable) unless absolutely necessary
  - Use 600/700 for sensitive files/directories
  - Consider group permissions for collaborative work
  - Test permission changes on non-critical files first
EOF
}