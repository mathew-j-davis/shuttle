# Shuttle Production Environment Setup Checklist
This checklist is a work in progress, features referred to may not be implemented
This checklist covers all requirements for setting up Shuttle in a production environment with Samba integration, scheduled processing, and proper security configuration.

## Phase 1: Pre-Production Planning

### 1.1 Architecture Review
- [ ] Review existing documentation:
  - [ ] `docs/samba-config.md` - Samba setup requirements
  - [ ] `docs/samba-writeonly-config.md` - Security-focused Samba configuration
  - [ ] `docs/run-cron-service-config.md` - Cron/service deployment guide
  - [ ] `docs/archive_handling_security.md` - Security considerations
  - [ ] `docs/environment_files.md` - Environment variable management

### 1.2 Service Account Creation
- [ ] Create primary service account: `sa-shuttle-run`
  - [ ] Full read/write access for scanning and processing
  - [ ] Shell set to `/usr/sbin/nologin` for security
  - [ ] Member of `shuttle-processors` group
- [ ] Create write-only service account: `sa-shuttle-lab`
  - [ ] Write-only access to inbox directory
  - [ ] Shell set to `/usr/sbin/nologin` for security
  - [ ] Member of `shuttle-writers` group

### 1.3 Directory Structure Planning
- [ ] Plan production directory layout:
  ```
  /srv/data/shuttle/
  ├── inbox/          # Write-only for submissions (770, group: shuttle-writers)
  ├── processed/      # Clean files after scanning (755, owner: sa-shuttle-run)
  ├── quarantine/     # Temporary isolation during scanning (700, owner: sa-shuttle-run)
  └── hazard/         # Encrypted malware archive (700, owner: sa-shuttle-run)
  
  /var/lib/shuttle/
  ├── tracking/       # Daily processing logs (755, owner: sa-shuttle-run)
  └── work/           # Test working directory (755, owner: sa-shuttle-run)
  
  /var/log/shuttle/   # Application logs (755, owner: sa-shuttle-run)
  /etc/shuttle/       # Configuration files (755, root:root)
  /opt/shuttle/       # Virtual environment (755, root:root)
  ```

## Phase 2: System Dependencies

### 2.1 Basic System Tools
- [ ] Install required packages:
  ```bash
  sudo apt-get update
  sudo apt-get install lsof gnupg git curl wget
  ```

### 2.2 Python Environment
- [ ] Install Python and development tools:
  ```bash
  sudo apt-get install python3 python3-pip python3-venv python3-dev
  ```

### 2.3 Antivirus Scanners
- [ ] Install ClamAV:
  ```bash
  sudo apt-get install clamav clamav-daemon
  sudo systemctl enable clamav-daemon
  sudo systemctl start clamav-daemon
  sudo freshclam  # Update virus definitions
  ```
- [ ] Configure Microsoft Defender (if available):
  - [ ] Verify `mdatp` command accessibility
  - [ ] Test scanning functionality: `run-shuttle-defender-test`

### 2.4 Samba Server
- [ ] Install Samba:
  ```bash
  sudo apt-get install samba samba-common-bin
  ```

## Phase 3: Samba Configuration

### 3.1 Samba Service Configuration
- [ ] Configure `/etc/samba/smb.conf` based on `docs/samba-config.md`
- [ ] Key settings:
  - [ ] Enable security auditing: `full_audit` VFS module
  - [ ] Set proper netbios name and workgroup
  - [ ] Configure proper authentication method
  - [ ] Enable encrypted passwords

### 3.2 Write-Only Share Configuration
- [ ] Configure secure write-only share based on `docs/samba-writeonly-config.md`:
  ```ini
  [shuttle-inbox]
  path = /srv/data/shuttle/inbox
  valid users = @shuttle-writers
  read only = no
  create mask = 0660
  directory mask = 0770
  force group = shuttle-writers
  vfs objects = full_audit
  full_audit:prefix = %u|%I|%S
  full_audit:success = write unlink rmdir mkdit
  full_audit:failure = all
  ```

### 3.3 Samba Security
- [ ] Set proper file permissions with ACLs:
  ```bash
  sudo setfacl -R -m g:shuttle-writers:rwx /srv/data/shuttle/inbox
  sudo setfacl -R -d -m g:shuttle-writers:rwx /srv/data/shuttle/inbox
  sudo chmod g+s /srv/data/shuttle/inbox  # setgid for inheritance
  ```
- [ ] Configure Samba users:
  ```bash
  sudo smbpasswd -a sa-shuttle-lab
  ```

### 3.4 Test Samba Configuration
- [ ] Test connectivity: `smbclient -L localhost -U sa-shuttle-lab`
- [ ] Test write access to inbox share
- [ ] Verify audit logging in `/var/log/samba/`

## Phase 4: Firewall Configuration

### 4.1 Samba Ports
- [ ] Open required Samba ports:
  ```bash
  sudo ufw allow 139/tcp    # NetBIOS Session Service
  sudo ufw allow 445/tcp    # SMB over TCP
  sudo ufw allow 137/udp    # NetBIOS Name Service
  sudo ufw allow 138/udp    # NetBIOS Datagram Service
  ```

### 4.2 SSH and Management
- [ ] Ensure SSH access is maintained:
  ```bash
  sudo ufw allow ssh
  ```

### 4.3 Enable Firewall
- [ ] Enable UFW if not already active:
  ```bash
  sudo ufw --force enable
  sudo ufw status verbose
  ```

## Phase 5: Shuttle Installation

### 5.1 GPG Key Generation
- [ ] Generate encryption keys:
  ```bash
  ./scripts/0_key_generation/00_generate_shuttle_keys.sh
  sudo cp shuttle_public.gpg /etc/shuttle/
  # Store private key securely offline
  ```

### 5.2 Virtual Environment Setup
- [ ] Create production virtual environment:
  ```bash
  sudo python3 -m venv /opt/shuttle/.venv
  sudo /opt/shuttle/.venv/bin/pip install --upgrade pip
  ```

### 5.3 Shuttle Installation
- [ ] Install Shuttle modules:
  ```bash
  cd /path/to/shuttle/source
  sudo /opt/shuttle/.venv/bin/pip install ./src/shared_library
  sudo /opt/shuttle/.venv/bin/pip install ./src/shuttle_defender_test_app
  sudo /opt/shuttle/.venv/bin/pip install ./src/shuttle_app
  ```

### 5.4 Configuration File
- [ ] Create `/etc/shuttle/config.conf` with production settings:
  ```ini
  [paths]
  source_path = /srv/data/shuttle/inbox
  destination_path = /srv/data/shuttle/processed
  quarantine_path = /srv/data/shuttle/quarantine
  hazard_archive_path = /srv/data/shuttle/hazard
  hazard_encryption_key_path = /etc/shuttle/shuttle_public.gpg
  log_path = /var/log/shuttle
  daily_processing_tracker_logs_path = /var/lib/shuttle/tracking
  
  [settings]
  on_demand_defender = true
  on_demand_clam_av = true
  max_scan_threads = 2
  delete_source_files_after_copying = true
  throttle = true
  throttle_free_space_mb = 1000
  throttle_max_file_count_per_day = 1000
  throttle_max_file_volume_per_day_mb = 10000
  
  [logging]
  log_level = INFO
  
  [notifications]
  notify = true
  recipient_email = admin@company.com
  recipient_email_error = errors@company.com
  recipient_email_summary = reports@company.com
  recipient_email_hazard = security@company.com
  smtp_server = mail.company.com
  smtp_port = 587
  smtp_username = shuttle@company.com
  use_tls = true
  # Note: Set smtp_password via environment variable
  ```

## Phase 6: Environment Configuration

### 6.1 Environment Variables
- [ ] Create `/etc/shuttle/shuttle_env.sh`:
  ```bash
  #!/bin/bash
  export SHUTTLE_CONFIG_PATH="/etc/shuttle/config.conf"
  export SHUTTLE_VENV_PATH="/opt/shuttle/.venv"
  export SHUTTLE_TEST_WORK_DIR="/var/lib/shuttle/work"
  export SHUTTLE_TEST_CONFIG_PATH="/var/lib/shuttle/work/test_config.conf"
  export PYTHONPATH="/opt/shuttle/.venv/lib/python3.*/site-packages:$PYTHONPATH"
  
  # SMTP password (set securely)
  export SHUTTLE_SMTP_PASSWORD="your_smtp_password_here"
  ```

### 6.2 Virtual Environment Activation
- [ ] Create `/etc/shuttle/shuttle_activate_virtual_environment.sh`:
  ```bash
  #!/bin/bash
  source /opt/shuttle/.venv/bin/activate
  ```

### 6.3 File Permissions
- [ ] Set proper ownership and permissions:
  ```bash
  sudo chown -R sa-shuttle-run:shuttle-processors /var/lib/shuttle
  sudo chown -R sa-shuttle-run:shuttle-processors /var/log/shuttle
  sudo chmod 755 /etc/shuttle/shuttle_env.sh
  sudo chmod 755 /etc/shuttle/shuttle_activate_virtual_environment.sh
  sudo chmod 600 /etc/shuttle/config.conf  # Protect config file
  ```

## Phase 7: Testing

### 7.1 Manual Testing
- [ ] Test configuration loading:
  ```bash
  sudo -u sa-shuttle-run bash -c "source /etc/shuttle/shuttle_env.sh && source /etc/shuttle/shuttle_activate_virtual_environment.sh && run-shuttle --help"
  ```

### 7.2 Defender Testing
- [ ] Test Microsoft Defender integration:
  ```bash
  sudo -u sa-shuttle-run bash -c "source /etc/shuttle/shuttle_env.sh && source /etc/shuttle/shuttle_activate_virtual_environment.sh && run-shuttle-defender-test"
  ```

### 7.3 End-to-End Testing
- [ ] Create test file in inbox via Samba
- [ ] Run Shuttle manually to process test file
- [ ] Verify file appears in processed directory
- [ ] Check logs for proper operation

## Phase 8: Cron Job Configuration

### 8.1 Cron Environment Setup
- [ ] Add environment sourcing to crontab for `sa-shuttle-run`:
  ```bash
  # Shuttle environment variables
  SHUTTLE_CONFIG_PATH="/etc/shuttle/config.conf"
  SHUTTLE_VENV_PATH="/opt/shuttle/.venv"
  SHUTTLE_TEST_WORK_DIR="/var/lib/shuttle/work"
  SHUTTLE_TEST_CONFIG_PATH="/var/lib/shuttle/work/test_config.conf"
  SHUTTLE_SMTP_PASSWORD="your_smtp_password_here"
  ```

### 8.2 Defender Test Schedule
- [ ] Add defender test cron job (weekly):
  ```bash
  # Run Defender test weekly on Sundays at 2 AM
  0 2 * * 0 /opt/shuttle/.venv/bin/run-shuttle-defender-test >/dev/null 2>&1
  ```

### 8.3 Shuttle Processing Schedule
- [ ] Add main processing cron job:
  ```bash
  # Run Shuttle every 15 minutes during business hours
  */15 8-18 * * 1-5 timeout 900 /opt/shuttle/.venv/bin/run-shuttle >/dev/null 2>&1
  
  # Daily cleanup and summary at 11 PM
  0 23 * * * /opt/shuttle/.venv/bin/run-shuttle --daily-summary >/dev/null 2>&1
  ```

### 8.4 Cron Monitoring
- [ ] Add cron job monitoring:
  - [ ] Log cron execution to syslog
  - [ ] Set up alerts for failed executions
  - [ ] Monitor disk space and processing metrics

## Phase 9: System Service Configuration (Optional)

### 9.1 Systemd Service Creation
- [ ] Create `/etc/systemd/system/shuttle.service`:
  ```ini
  [Unit]
  Description=Shuttle File Transfer and Scanning Service
  After=network.target multi-user.target
  Wants=network.target
  
  [Service]
  Type=simple
  User=sa-shuttle-run
  Group=shuttle-processors
  UMask=0113
  ExecStart=/opt/shuttle/.venv/bin/run-shuttle --daemon
  Restart=on-failure
  RestartSec=300
  TimeoutStartSec=60
  TimeoutStopSec=30
  
  # Resource limits
  LimitNOFILE=1024
  LimitNPROC=64
  
  # Environment
  Environment="SHUTTLE_CONFIG_PATH=/etc/shuttle/config.conf"
  Environment="SHUTTLE_VENV_PATH=/opt/shuttle/.venv"
  Environment="SHUTTLE_TEST_WORK_DIR=/var/lib/shuttle/work"
  EnvironmentFile=-/etc/shuttle/shuttle_env.sh
  
  [Install]
  WantedBy=multi-user.target
  ```

### 9.2 Service Management
- [ ] Enable and start service:
  ```bash
  sudo systemctl daemon-reload
  sudo systemctl enable shuttle.service
  sudo systemctl start shuttle.service
  sudo systemctl status shuttle.service
  ```

## Phase 10: Monitoring and Maintenance

### 10.1 Log Rotation
- [ ] Configure logrotate for Shuttle logs:
  ```bash
  # Create /etc/logrotate.d/shuttle
  /var/log/shuttle/*.log {
      daily
      rotate 30
      compress
      delaycompress
      missingok
      notifempty
      create 644 sa-shuttle-run shuttle-processors
      postrotate
          systemctl reload shuttle.service || true
      endscript
  }
  ```

### 10.2 Monitoring Setup
- [ ] Set up monitoring for:
  - [ ] Disk space on all Shuttle directories
  - [ ] Processing queue length in inbox
  - [ ] Daily processing metrics from tracker logs
  - [ ] Email notification delivery
  - [ ] Cron job execution status

### 10.3 Backup Configuration
- [ ] Include in backup strategy:
  - [ ] `/etc/shuttle/` (configuration)
  - [ ] `/var/lib/shuttle/tracking/` (processing history)
  - [ ] `/srv/data/shuttle/processed/` (clean files, if needed)
  - [ ] Samba configuration and audit logs

### 10.4 Security Auditing
- [ ] Regular security reviews:
  - [ ] Review Samba audit logs
  - [ ] Monitor failed login attempts
  - [ ] Check file permission integrity
  - [ ] Review hazard archive for trends
  - [ ] Update virus definitions regularly

## Phase 11: Documentation and Handover

### 11.1 Operational Documentation
- [ ] Document operational procedures:
  - [ ] How to check processing status
  - [ ] How to manually run Shuttle
  - [ ] Troubleshooting common issues
  - [ ] Emergency shutdown procedures

### 11.2 Contact Information
- [ ] Ensure notification emails reach appropriate teams:
  - [ ] `recipient_email_error` → IT Operations
  - [ ] `recipient_email_summary` → Management/Reports
  - [ ] `recipient_email_hazard` → Security Team

### 11.3 Change Management
- [ ] Establish procedures for:
  - [ ] Configuration changes
  - [ ] Shuttle software updates
  - [ ] Adding new user access
  - [ ] Modifying scan policies

## Validation Checklist

### Final Verification
- [ ] All service accounts created and configured
- [ ] Samba shares accessible with proper permissions
- [ ] Firewall rules applied and tested
- [ ] Shuttle processes files end-to-end successfully
- [ ] Cron jobs scheduled and running
- [ ] Email notifications working for all types
- [ ] Logs rotating properly
- [ ] Monitoring alerts configured
- [ ] Documentation complete and accessible

### Performance Testing
- [ ] Test with various file types and sizes
- [ ] Verify throttling works under load
- [ ] Test malware detection and quarantine
- [ ] Confirm email notifications under error conditions
- [ ] Validate backup and restore procedures

## Troubleshooting Resources

- **Configuration Issues**: Check `/var/log/shuttle/` and `journalctl -u shuttle`
- **Samba Problems**: Review `/var/log/samba/` and test with `smbclient`
- **Cron Issues**: Check `/var/log/cron` and `systemctl status cron`
- **Permission Problems**: Verify ACLs with `getfacl` and ownership with `ls -la`
- **Email Issues**: Test SMTP connectivity and check authentication

## Security Considerations

Based on `docs/archive_handling_security.md`:
- Archive files are processed with strict resource limits
- Maximum compression ratio of 100:1 to prevent zip bombs
- Maximum extracted size of 1GB
- Process timeouts to prevent hung operations
- All malware encrypted before storage in hazard archive

This checklist ensures a secure, monitored, and automated Shuttle deployment ready for production file processing workloads.