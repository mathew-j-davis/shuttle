 User Account Configuration Matrix

  | Account Type    | Home Directory | Shell            | Setup Status | Resources Present        | Can Do                    | Cannot Do                       | Typical Use Case                          |
  |-----------------|----------------|------------------|--------------|--------------------------|---------------------------|---------------------------------|-------------------------------------------|
  | Domain Account  | ✓ Yes          | ✓ /bin/bash      | ✓ Set up     | - Home dir exists        | - Interactive login       |                                 | Regular domain users needing Linux access |
  |                 |                |                  |              | - In local groups        | - Run cron jobs           |                                 |                                           |
  |                 |                |                  |              | - Shell configs          | - Run services            |                                 |                                           |
  |                 |                |                  |              |                          | - Access group resources  |                                 |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Domain Account  | ✓ Yes          | ✗ /sbin/nologin  | ✓ Set up     | - Home dir exists        | - Run services            | - Interactive login             | Service accounts with file storage needs  |
  |                 |                |                  |              | - In local groups        | - Run cron jobs           | - SSH shell access              |                                           |
  |                 |                |                  |              | - No shell configs       | - SFTP/SCP only           |                                 |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Domain Account  | ✗ No           | ✗ /sbin/nologin  | ✓ Set up     | - In local groups        | - Run services            | - Interactive login             | Pure service accounts (most common)       |
  |                 |                |                  |              | - No home dir            | - Run cron jobs           | - Store personal files          |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Domain Account  | ✗ No           | ✓ /bin/bash      | ✓ Set up     | - In local groups        | - Run services            | - Store personal files          | Unusual - typically misconfigured         |
  |                 |                |                  |              | - No home dir            | - Run cron jobs           | - Full interactive experience   |                                           |
  |                 |                |                  |              |                          | - Limited interactive*    |                                 |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Domain Account  | -              | -                | ✗ Not set up | - Visible via NSS only   | - Authenticate            | - Access local groups           | Domain user with no local configuration   |
  |                 |                |                  |              |                          | - Basic access            | - Run services                  |                                           |
  |                 |                |                  |              |                          |                           | - Use cron                      |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Local Account   | ✓ Yes          | ✓ /bin/bash      | N/A          | - Home dir exists        | - Everything              | -                               | Standard local user                       |
  |                 |                |                  |              | - In groups              |                           |                                 |                                           |
  |                 |                |                  |              | - Shell configs          |                           |                                 |                                           |
  |                 |                |                  |              | - /etc/passwd entry      |                           |                                 |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Local Account   | ✓ Yes          | ✗ /sbin/nologin  | N/A          | - Home dir exists        | - Run services            | - Interactive login             | Local service account with storage        |
  |                 |                |                  |              | - In groups              | - SFTP/SCP only           |                                 |                                           |
  |                 |                |                  |              | - /etc/passwd entry      |                           |                                 |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |
  | Local Account   | ✗ No           | ✗ /sbin/nologin  | N/A          | - In groups              | - Run services only       | - Interactive login             | System service accounts                   |
  |                 |                |                  |              | - /etc/passwd entry      |                           | - Store files                   |                                           |
  |                 |                |                  |              |                          |                           |                                 |                                           |

  Key Insights for Code Implementation:

  1. "Set up" for Domain Accounts Means:

  - Added to required local groups
  - Home directory created (if needed)
  - Proper ownership set on home directory
  - Shell configuration files created (if interactive shell)

  2. Shell vs Home Directory are Independent:

  - No shell (/sbin/nologin, /bin/false): Prevents interactive login but allows service execution
  - No home directory: User can still run processes but has no personal storage

  3. Domain vs Local Detection:

  # Domain user exists in domain but not "set up locally":
  getent passwd "DOMAIN\\username"  # Returns user info
  ls -la /home/username            # No directory
  groups "DOMAIN\\username"        # Only domain groups, no local groups

  # Domain user "set up locally":
  getent passwd "DOMAIN\\username"  # Returns user info
  ls -la /home/username            # Directory exists (if created)
  groups "DOMAIN\\username"        # Shows local groups too

  4. Service Account Best Practices:

  - Usually: No home directory + No shell
  - Sometimes: No home directory + Shell (for debugging/maintenance)
  - Rarely: Home directory + No shell (for services needing persistent storage)

  5. Code Implications:

  Your check_domain_user_exists_locally() should check for:
  - Local group memberships (most important)
  - Home directory (only if it was supposed to be created)
  - NOT just whether the user exists in NSS