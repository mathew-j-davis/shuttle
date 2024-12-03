import os
import subprocess
import win32api
import win32con
import win32security
import ctypes



# [DEFAULT]
# SourcePath=\\server\share
# DestinationPath=C:\Users\YourUsername\Documents\Destination
#  QuarantinePath=C:\Temp\ShuttleTemp
#   LogPath=C:\Logs
#    pip install pywin32

def get_user_sid(username):
    try:
        sid, domain, type = win32security.LookupAccountName(None, username)
        return win32security.ConvertSidToStringSid(sid)
    except Exception as e:
        return f"Unable to get SID for {username}: {e}"

# Current username
current_username = os.getenv('USERNAME')

# Full name: ComputerName\Username
computer_name = os.getenv('COMPUTERNAME')
full_name = f"{computer_name}\\{current_username}"

# Current user (domain\username)
current_user = win32api.GetUserNameEx(win32con.NameSamCompatible)

# Whoami output
try:
    whoami_output = subprocess.check_output('whoami', shell=True, universal_newlines=True).strip()
except subprocess.CalledProcessError as e:
    whoami_output = f"Error executing whoami: {e}"

# User SID
user_sid = get_user_sid(current_username)

print(f"Current username: {current_username}")
print(f"Full name: {full_name}")
print(f"Current user (domain\\username): {current_user}")
print(f"Whoami output: {whoami_output}")
print(f"User SID: {user_sid}")
