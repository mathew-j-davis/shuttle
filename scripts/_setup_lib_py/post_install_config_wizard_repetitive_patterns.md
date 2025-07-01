# Post Install Config Wizard - Repetitive Code Analysis

## Analysis of `len(groups)` Patterns

### Pattern 1: Group Selection Menu (Appears 6 times)

This pattern appears repeatedly throughout the code:

```python
# Get sorted groups
groups = sorted(self.config['groups'].keys())

# Display numbered list
for i, name in enumerate(groups, 1):
    print(f"{i}) {name}")

# Create valid choices including 0
valid_choices = [str(i) for i in range(0, len(groups) + 1)]

# Get user choice
choice_str = self._get_choice("Select group number...", valid_choices, "0")
idx = int(choice_str)

# Handle selection
if idx == 0:
    return/cancel/custom
if 1 <= idx <= len(groups):
    selected_group = groups[idx - 1]
```

### Occurrences Found:

1. **Line 1871** - `_custom_remove_group()` - Remove group from instructions
2. **Line 1911** - `_custom_edit_group()` - Edit group in instructions  
3. **Line 2059** - `_custom_add_user()` - Select primary group for new user
4. **Line 2221** - `_custom_edit_user()` - Edit user's primary group
5. **Line 2593** - `_custom_configure_path_permissions()` - Select group for path ownership
6. **Line 2651** - `_custom_configure_path_permissions()` - Select group for ACL permissions

### Common Elements:

1. **Sorting groups**: `groups = sorted(self.config['groups'].keys())`
2. **Enumeration display**: `for i, name in enumerate(groups, 1):`
3. **Valid choices generation**: `[str(i) for i in range(0, len(groups) + 1)]`
4. **Index validation**: `if 1 <= idx <= len(groups):`
5. **Group retrieval**: `groups[idx - 1]`

### Variations:

- Some include option "0) No primary group" or "0) Cancel"
- Line 2221 adds "-1" to valid_choices for "keep current" option
- Some show current selection with "(current)" marker

## Recommended Refactoring

### Option 1: Create a Generic Group Selection Method

```python
def _select_group_from_list(self, prompt: str, include_none: bool = False, 
                           none_label: str = "Cancel", current_group: str = None) -> Optional[str]:
    """
    Generic group selection menu
    
    Returns:
        Selected group name, None if cancelled/none selected
    """
    groups = sorted(self.config['groups'].keys())
    
    if not groups:
        print("No groups available")
        return None
    
    # Display groups
    for i, name in enumerate(groups, 1):
        current = " (current)" if name == current_group else ""
        print(f"{i}) {name}{current}")
    
    if include_none:
        print(f"0) {none_label}")
    
    # Get selection
    valid_choices = [str(i) for i in range(0 if include_none else 1, len(groups) + 1)]
    default = "0" if include_none else "1"
    
    try:
        choice_str = self._get_choice(prompt, valid_choices, default)
        idx = int(choice_str)
        
        if idx == 0 and include_none:
            return None
        if 1 <= idx <= len(groups):
            return groups[idx - 1]
    except ValueError:
        pass
    
    return None
```

### Option 2: Use the Existing Dynamic Menu System

Since the codebase already has `_get_menu_choice()` and `_build_user_template_menu()`, extend this pattern:

```python
def _build_group_menu(self, include_none: bool = False, none_label: str = "Cancel",
                     current_group: str = None) -> List[Dict[str, Any]]:
    """Build dynamic group selection menu"""
    menu_items = []
    
    if include_none:
        menu_items.append({
            'key': '0',
            'label': none_label,
            'value': None
        })
    
    groups = sorted(self.config['groups'].keys())
    for i, group_name in enumerate(groups, 1):
        label = group_name
        if group_name == current_group:
            label += " (current)"
        
        menu_items.append({
            'key': str(i),
            'label': label,
            'value': group_name
        })
    
    return menu_items
```

## Other Repetitive Patterns to Investigate

1. **User selection menus** - Similar pattern for selecting users
2. **Path selection menus** - Similar pattern for selecting paths
3. **Yes/No confirmations** - Could use existing `_confirm()` method more
4. **Validation patterns** - Group/user/path existence checks
5. **Permission display** - Showing current permissions in various contexts

## Additional Repetitive Patterns Found

### Pattern 2: Sorted Groups Retrieval
- **Occurrences**: 8 times
- **Pattern**: `groups = sorted(self.config['groups'].keys())`
- **Could be**: A property or method like `self._get_sorted_groups()`

### Pattern 3: Enumeration for Display
- **Occurrences**: 16 times throughout the file
- **Pattern**: `for i, item in enumerate(collection, 1):`
- **Used for**: Groups, users, permissions, paths, etc.

### Pattern 4: User Selection (Similar to Group Selection)
```python
users = sorted([u['name'] for u in self.users])
for i, name in enumerate(users, 1):
    print(f"{i}) {name}")
# ... similar selection logic
```

### Pattern 5: Permission Entry
Multiple places ask for permission mode with similar validation:
```python
mode = input("Mode (e.g., 755) [755]: ").strip() or "755"
# Validation of octal mode
```

## Benefits of Refactoring

1. **Reduce code size**: ~50-70 lines per occurrence × 6 = 300-420 lines saved
2. **Consistency**: All group selections work the same way
3. **Maintainability**: Fix bugs or add features in one place
4. **Testability**: Test the selection logic once
5. **Extensibility**: Easy to add new features (search, filtering, etc.)

## Group Logic Analysis

### Embedded Validation Logic Found

After thorough analysis, I found several pieces of group validation logic embedded in longer functions that should be extracted:

#### 1. GID Validation (Lines 1790-1799 in `_custom_add_custom_group`)
```python
if gid_str:
    try:
        gid = int(gid_str)
        if gid < 1000:
            if not self._confirm("GID < 1000 is typically for system groups. Continue?", False):
                return
        group_data['gid'] = gid
    except ValueError:
        print("❌ Invalid GID")
        return
```

#### 2. Group Name Validation (Multiple locations)
- Empty name check: Line 1775-1777
- Duplicate group check: Lines 1779-1781, 3098-3100
- **Missing**: Check if group name conflicts with existing usernames

#### 3. Group Usage Check (Lines 1879-1890 in `_custom_remove_group`)
```python
# Check if group is used by any users
users_using = []
for user in self.users:
    if (user.get('groups', {}).get('primary') == group_name or 
        group_name in user.get('groups', {}).get('secondary', [])):
        users_using.append(user['name'])
```

#### 4. Group Data Structure Validation (Lines 3102-3110)
- Validates dict type
- Validates required 'description' field
- **Missing**: GID uniqueness check

### Recommended Refactoring

Create dedicated validation methods:

```python
def _validate_group_name(self, group_name: str, check_users: bool = True) -> tuple[bool, str]:
    """Validate group name against rules and existing entities
    
    Returns:
        (is_valid, error_message)
    """
    if not group_name:
        return False, "Group name cannot be empty"
    
    if group_name in self.config['groups']:
        return False, f"Group '{group_name}' already exists"
    
    if check_users:
        # Check against existing usernames to avoid conflicts
        for user in self.users:
            if user['name'] == group_name:
                return False, f"Group name '{group_name}' conflicts with existing username"
    
    # Add more validation rules (e.g., valid characters, length)
    if not group_name.replace('_', '').replace('-', '').isalnum():
        return False, "Group name must contain only letters, numbers, underscores, and hyphens"
    
    return True, ""

def _validate_gid(self, gid: int, group_name: str = None) -> tuple[bool, str]:
    """Validate GID value and check for conflicts
    
    Returns:
        (is_valid, error_message)
    """
    if gid < 0:
        return False, "GID must be non-negative"
    
    # Check for GID conflicts
    for name, data in self.config['groups'].items():
        if name != group_name and data.get('gid') == gid:
            return False, f"GID {gid} already used by group '{name}'"
    
    # Warning for system GIDs
    if gid < 1000:
        return True, "WARNING: GID < 1000 is typically for system groups"
    
    return True, ""

def _find_groups_using_user(self, group_name: str) -> List[str]:
    """Find all users that reference a group
    
    Returns:
        List of usernames using the group
    """
    users_using = []
    for user in self.users:
        if (user.get('groups', {}).get('primary') == group_name or 
            group_name in user.get('groups', {}).get('secondary', [])):
            users_using.append(user['name'])
    return users_using

def _get_next_available_gid(self, start_gid: int = 5000) -> int:
    """Find next available GID starting from start_gid"""
    used_gids = set()
    for group_data in self.config['groups'].values():
        if 'gid' in group_data:
            used_gids.add(group_data['gid'])
    
    gid = start_gid
    while gid in used_gids:
        gid += 1
    return gid
```

### Additional Group-Related Patterns

#### 5. Secondary Group Selection (Lines 2068-2083)
```python
print("\nAdd to secondary groups (comma-separated numbers, or blank for none):")
available_groups = [g for g in sorted(self.config['groups'].keys()) 
                   if g != user['groups']['primary']]
for i, name in enumerate(available_groups, 1):
    print(f"{i}) {name}")

group_input = input("Groups: ").strip()
if group_input:
    try:
        indices = [int(x.strip()) for x in group_input.split(',')]
        for idx in indices:
            if 1 <= idx <= len(available_groups):
                user['groups']['secondary'].append(available_groups[idx - 1])
    except ValueError:
        print("⚠️  Invalid group selection")
```

This pattern appears multiple times and could be refactored into:
```python
def _select_multiple_groups(self, prompt: str, exclude_groups: List[str] = None) -> List[str]:
    """Select multiple groups from available list"""
    # Implementation here
```

### Summary of Group Logic Issues

1. **GID validation** is embedded in multiple places
2. **Group name validation** lacks username conflict checking
3. **Group usage checking** is repeated in removal logic
4. **No GID uniqueness validation**
5. **Secondary group selection** uses comma-separated input (inconsistent with other menus)
6. **No helper to get sorted groups** (repeated 8 times)
7. **No automatic GID assignment** helper

### Benefits of Extracting Group Logic

1. **Reusability**: Same validation used everywhere
2. **Consistency**: All group operations follow same rules
3. **Testability**: Can unit test validation logic
4. **Maintainability**: Fix bugs or add rules in one place
5. **Completeness**: Easy to see what validation is missing
6. **Error Prevention**: Catch conflicts before they cause issues

## Recommended Approach

Given that the codebase already has:
- `_get_menu_choice()` - Generic menu display
- `_find_default_key()` - Smart default selection
- `_get_choice_value()` - Value extraction

The best approach would be to:
1. Extract all validation logic into dedicated methods
2. Extend the menu system for groups, users, and paths selection
3. Create consistent validation throughout the wizard