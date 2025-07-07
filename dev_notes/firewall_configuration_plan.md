# Firewall Configuration Plan for REMOTE VM

## Current Situation
- **VM Being Configured**: REMOTE
- **Your Workstation**: LOCAL_DEV
- **Special Host**: ISOLATED (needs restricted access)
- **Network**: NETWORK (general network access)

## Requirements Summary
1. ✅ Allow Samba access to share '/in' from ISOLATED
2. ✅ Allow Samba access to share '/in' from LOCAL_DEV
3. 🚫 Block Samba access from all other locations
4. 🚫 Block ALL other services from ISOLATED (only Samba allowed)
5. 🔓 Leave all other access from NETWORK and LOCAL_DEV unchanged

## CRITICAL: Pre-Configuration Safety Steps

### Step 1: Get IP Addresses
First, we need the IP addresses. Run these on each machine:
```bash
# On LOCAL_DEV:
ip addr show | grep inet

# On ISOLATED:
ip addr show | grep inet

# Get NETWORK subnet info if needed
```

### Step 2: Backup Current Firewall Rules
```bash
# On REMOTE VM - ALWAYS DO THIS FIRST!
sudo ufw status numbered > ~/firewall_backup_$(date +%Y%m%d_%H%M%S).txt
sudo iptables-save > ~/iptables_backup_$(date +%Y%m%d_%H%M%S).txt
```

### Step 3: Test Current Access
Before making changes, verify current access:
```bash
# From LOCAL_DEV - test SSH (so you don't lock yourself out!)
ssh user@REMOTE

# Test current Samba access if configured
smbclient -L //REMOTE -U username
```

## Safe Configuration Steps

### Step 1: Check Current Firewall Status
```bash
# On REMOTE VM
./scripts/2_post_install_config_steps/14_configure_firewall.sh show-status
./scripts/2_post_install_config_steps/14_configure_firewall.sh list-firewall-rules
```

### Step 2: Configure Host Isolation for ISOLATED (CAREFULLY!)
This is the most dangerous step - we're isolating ISOLATED to ONLY Samba:

```bash
# First, do a DRY RUN to see what will happen
./scripts/2_post_install_config_steps/14_configure_firewall.sh isolate-host \
  --host <ISOLATED_IP> \
  --allowed-services samba \
  --comment "Isolated host - Samba only access" \
  --dry-run

# Review the output carefully!
# If it looks correct, run without --dry-run
```

### Step 3: Allow Samba from Specific Hosts
```bash
# Allow from LOCAL_DEV (your workstation)
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from \
  --source <LOCAL_DEV_IP> \
  --comment "Samba access from LOCAL_DEV workstation" \
  --dry-run

# Allow from ISOLATED
./scripts/2_post_install_config_steps/14_configure_firewall.sh allow-samba-from \
  --source <ISOLATED_IP> \
  --comment "Samba access from ISOLATED host" \
  --dry-run
```

### Step 4: Deny Samba from All Others
```bash
# Block Samba from everywhere else
./scripts/2_post_install_config_steps/14_configure_firewall.sh deny-service-from \
  --service samba \
  --sources "0.0.0.0/0" \
  --comment "Block Samba from all other sources" \
  --dry-run
```

## IMPORTANT: Order Matters!

Firewall rules are processed in order. The correct sequence is:
1. **ALLOW** specific hosts (LOCAL_DEV, ISOLATED) for Samba
2. **DENY** Samba from all others (0.0.0.0/0)
3. **ISOLATE** the ISOLATED host (this adds deny rules for other services)

## Verification Commands

After applying rules:
```bash
# Check the final ruleset
./scripts/2_post_install_config_steps/14_configure_firewall.sh list-firewall-rules

# Check isolated hosts
./scripts/2_post_install_config_steps/14_configure_firewall.sh list-isolated-hosts

# Check Samba-specific rules
./scripts/2_post_install_config_steps/14_configure_firewall.sh list-samba-rules
```

## Testing After Configuration

### From LOCAL_DEV:
```bash
# Test SSH still works (critical!)
ssh user@REMOTE

# Test Samba access
smbclient //REMOTE/in -U domain_user
```

### From ISOLATED:
```bash
# Test Samba works
smbclient //REMOTE/in -U domain_user

# Test SSH is blocked (should fail)
ssh user@REMOTE  # This should timeout/fail
```

### From another host:
```bash
# Test Samba is blocked
smbclient //REMOTE/in -U domain_user  # Should fail
```

## Emergency Rollback

If something goes wrong and you're locked out:
1. If you have console access to REMOTE VM:
   ```bash
   sudo ufw disable
   # or
   sudo ufw --force reset
   ```

2. If you saved the iptables rules:
   ```bash
   sudo iptables-restore < ~/iptables_backup_[date].txt
   ```

## Alternative Approach Using YAML

Instead of command-by-command, you could create a complete firewall.yaml:

```yaml
firewall:
  enabled: true
  default_policy:
    incoming: deny
    outgoing: allow
  rules:
    # Allow SSH from your workstation (IMPORTANT - don't lock yourself out!)
    ssh_admin:
      service: ssh
      action: allow
      sources: ["LOCAL_DEV_IP"]
      comment: "SSH from admin workstation"
    
    # Samba access for specific hosts
    samba_access:
      service: samba
      action: allow
      sources: ["LOCAL_DEV_IP", "ISOLATED_IP"]
      comment: "Samba access from authorized hosts only"
  
  # Host isolation
  isolated_hosts:
    - host: "ISOLATED_IP"
      allowed_services: ["samba"]
      comment: "Isolated host - Samba access only"
```

## Critical Reminders

1. **ALWAYS test with --dry-run first**
2. **NEVER disable SSH from your workstation (LOCAL_DEV)**
3. **Have console access ready as backup**
4. **Document all IP addresses before starting**
5. **Test incrementally - don't apply all rules at once**

Would you like me to help you:
1. Create the exact commands with your actual IP addresses?
2. Create a test plan to verify each step?
3. Create a YAML configuration file instead?