import os
import subprocess
import pwd
import grp

def get_user_info():
    # Current username
    current_username = os.getenv('USER')

    # User's home directory
    home_directory = os.path.expanduser('~')

    # UID and GID
    uid = os.getuid()
    gid = os.getgid()

    # Full name (GECOS field)
    try:
        pw_record = pwd.getpwnam(current_username)
        full_name = pw_record.pw_gecos.split(',')[0]
    except KeyError:
        full_name = 'Unknown'

    # Groups the user belongs to
    groups = [g.gr_name for g in grp.getgrall() if current_username in g.gr_mem]
    primary_group = grp.getgrgid(gid).gr_name

    # Whoami output
    try:
        whoami_output = subprocess.check_output('whoami', shell=True, universal_newlines=True).strip()
    except subprocess.CalledProcessError as e:
        whoami_output = f"Error executing whoami: {e}"

    print(f"Current username: {current_username}")
    print(f"Full name: {full_name}")
    print(f"UID: {uid}")
    print(f"GID: {gid}")
    print(f"Primary group: {primary_group}")
    print(f"Supplementary groups: {', '.join(groups)}")
    print(f"Home directory: {home_directory}")
    print(f"Whoami output: {whoami_output}")

def check_access_to_paths(settings_file='~/.shuttle/settings.ini'):

    settings_file = os.path.expanduser(settings_file)
    # Read settings from the file
    settings = {}
    if os.path.exists(settings_file):
        with open(settings_file, 'r') as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    settings[key.strip()] = value.strip()
    else:
        print(f"Settings file '{settings_file}' not found.")
        return

    paths_to_check = ['SourcePath', 'DestinationPath', 'QuarantinePath', 'QuarantineHazardArchive', 'LogPath']
    current_username = os.getenv('USER')
    all_access = True

    for path_key in paths_to_check:
        path = settings.get(path_key)
        if path:
            # Expand user and environment variables
            path = os.path.expandvars(os.path.expanduser(path))
            can_read = os.access(path, os.R_OK)
            can_write = os.access(path, os.W_OK)
            can_execute = os.access(path, os.X_OK)

            # File or directory?
            if os.path.isdir(path):
                path_type = 'Directory'
            elif os.path.isfile(path):
                path_type = 'File'
            else:
                path_type = 'Non-existent path'

            print(f"\n{path_key}: {path}")
            print(f"  Path type: {path_type}")
            print(f"  Readable: {'Yes' if can_read else 'No'}")
            print(f"  Writable: {'Yes' if can_write else 'No'}")
            print(f"  Executable: {'Yes' if can_execute else 'No'}")

            if not (can_read and can_write):
                all_access = False
                print(f"  Warning: User '{current_username}' may not have sufficient permissions for '{path_key}'.")

        else:
            print(f"\n{path_key} not specified in settings.")

    if all_access:
        print("\nUser has sufficient access to all specified paths.")
    else:
        print("\nUser may not have sufficient access to some paths.")

if __name__ == "__main__":

    print("User Information:")
    get_user_info()
    print("\nChecking access to paths in ~/.shuttle/settings.ini:")
    check_access_to_paths()
