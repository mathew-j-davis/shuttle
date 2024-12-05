import keyring
import getpass

def store_password():
    service_name = "shuttle_linux"
    username = "hazard_archive"

    # Prompt the user to enter the password twice
    password = getpass.getpass("Enter the hazard archive password: ")
    confirm_password = getpass.getpass("Confirm the hazard archive password: ")

    if password != confirm_password:
        print("Passwords do not match. Please try again.")
        return

    # Store the password in the keyring
    keyring.set_password(service_name, username, password)
    print("Password stored successfully in the keyring.")

if __name__ == "__main__":
    store_password() 