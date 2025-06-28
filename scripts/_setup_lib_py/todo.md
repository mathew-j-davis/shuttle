# TODO for Shuttle Setup Scripts

## File Creation Mode
- [ ] **CHOSEN APPROACH: Set umask in Python code**
  - [ ] Add `os.umask(0o007)` at the beginning of shuttle main() function
  - [ ] This ensures files=660, dirs=770 regardless of how shuttle is invoked
  - [ ] Applies to all shuttle execution methods: systemd, cron, manual, script calls
- [ ] Document the chosen approach in deployment guide
- [ ] Consider different modes for different file types:
  - Data files in source/destination: 0660 (handled by umask)
  - Log files: 0664 → will be 0660 with umask 0007 (more secure)
  - Temporary files in quarantine: 0660 (handled by umask)
  - Ledger entries: 0640 → will be 0660 with umask 0007 (acceptable)

## Other Permission-Related Items
- [ ] Document standard permission templates for all shuttle paths
- [ ] Create permission validation script to verify correct setup
- [ ] Consider ACL inheritance rules for subdirectories

## Security Audit Tool
- [ ] Create an audit tool to verify security configuration:
  - [ ] Check Samba user restrictions:
    - Members of `shuttle_samba_in_users` should NOT be members of any other groups
    - Should have `/usr/sbin/nologin` or `/bin/false` as shell (no login capability)
    - Should not have home directories (or have them disabled)
    - Cannot have individual umask settings (controlled by Samba)
  - [ ] Similar checks for `shuttle_samba_out_users`
  - [ ] Verify file permissions in all shuttle directories
  - [ ] Check for any files with execute permissions in data directories
  - [ ] Verify default ACLs are properly set
  - [ ] Check for any files readable by "others"
  - [ ] Validate group memberships follow security model