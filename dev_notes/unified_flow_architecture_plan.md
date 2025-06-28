# Unified Flow Architecture Plan

## Analysis Summary

Based on analysis of the post_install_config_wizard.py file, here's the current structure of the three configuration modes and proposed unification approach.

## Current Mode Analysis

### **1. Simple Mode (`_run_simple_mode`)**

**Purpose**: Single admin user with full access for development/testing

**Flow**:
1. **Setup**: Apply mode-specific defaults (development environment, interactive mode)
2. **Choice Point**: Accept all defaults OR step-by-step configuration
3. **If accepting defaults**:
   - Use `DEVELOPMENT_COMPONENT_DEFAULTS` (all components enabled)
   - Create single admin group via `get_development_admin_group()`
   - Create default admin user via `_create_default_admin_user()`
   - Configure development paths via `_configure_development_paths()`
4. **If step-by-step**:
   - Component selection via `_development_mode_components()`
   - Create hardcoded admin group
   - Interactive admin user creation with optional Samba
   - Configure development paths via `_configure_development_paths()`
5. **Finalize**: Return complete config via `_build_complete_config()`

**Data Sources**: Hardcoded defaults, user input for customization

### **2. Standard Mode (`_run_standard_mode`)**

**Purpose**: Production security model with proper user separation

**Flow**:
1. **Setup**: Apply mode-specific defaults (production environment, non-interactive mode)
2. **Choice Point**: Accept all defaults OR step-by-step configuration
3. **If accepting defaults**:
   - Enable all production components manually
   - Create standard groups via `_create_standard_groups()`
   - Create all standard roles via `_create_all_standard_roles_with_defaults()`
   - Configure standard paths via `_configure_standard_paths()`
4. **If step-by-step**:
   - Component selection via `_standard_mode_components()`
   - Create standard groups via `_create_standard_groups()`
   - Select and create roles via `_select_and_create_standard_roles()`
   - Configure standard paths via `_configure_standard_paths()`
5. **Finalize**: Return complete config via `_build_complete_config()`

**Data Sources**: Imported functions from `standard_configs` module (`get_standard_groups`, `get_standard_path_permissions`, `get_standard_user_templates`)

### **3. Custom Mode (`_run_custom_mode`)**

**Purpose**: Interactive builder for completely custom configurations

**Flow**:
1. **Setup**: 
   - If base_config provided (customizing standard): Load existing config
   - If from scratch: Set custom mode defaults
2. **Main Loop**: Interactive menu-driven configuration:
   - **1**: Manage Groups (`_custom_manage_groups`)
   - **2**: Manage Users (`_custom_manage_users`) 
   - **3**: Configure Path Permissions (`_custom_configure_path_permissions`)
   - **4**: Configure Components (`_custom_manage_components`)
   - **5**: Import Templates (`_custom_import_template`)
   - **6**: Show Configuration (`_custom_show_configuration`)
   - **7**: Validate Configuration (`_custom_validate_configuration`)
   - **d**: Delete and return to main menu
   - **r**: Reset configuration
   - **s**: Save and exit
3. **Finalize**: Return complete config via `_build_complete_config()`

**Data Sources**: Interactive user input, optional template imports

## Common Patterns and Shared Methods

### **Shared Helper Methods All Modes Use**:
1. **`_apply_mode_specific_defaults(mode)`** - Sets metadata and common settings
2. **`_build_complete_config()`** - Validates paths and builds final YAML documents
3. **`_confirm(question, default)`** - Standardized yes/no prompting
4. **`_get_choice(prompt, options, default)`** - Standardized option selection

### **Path Configuration Methods**:
- **`_configure_development_paths()`** - Used by simple mode
- **`_configure_standard_paths()`** - Used by standard mode  
- **`_custom_configure_path_permissions()`** - Used by custom mode

### **Component Configuration**:
- Simple: Uses `DEVELOPMENT_COMPONENT_DEFAULTS` constant
- Standard: Manual component enabling or `_standard_mode_components()`
- Custom: Interactive via `_custom_manage_components()`

### **Group/User Creation**:
- Simple: `get_development_admin_group()`, `_create_default_admin_user()`
- Standard: `_create_standard_groups()`, template-based user creation
- Custom: Interactive management methods

## Key Differences

1. **Data Sources**:
   - Simple: Hardcoded defaults and minimal user input
   - Standard: Imports from `standard_configs` module 
   - Custom: Fully user-driven

2. **Complexity**:
   - Simple: Linear flow with single choice point
   - Standard: Linear flow with two choice points
   - Custom: Loop-based menu system

3. **Target Use Case**:
   - Simple: Development/testing (minimal security)
   - Standard: Production (proper security model)
   - Custom: Specialized deployments (maximum flexibility)

## Helper Method Analysis

### 1. Component Selection Methods - Common Patterns

**Similarities:**
- All handle the same 5 components: `install_samba`, `configure_samba`, `install_acl`, `configure_users_groups`, `configure_firewall`
- All use the same `_confirm()` utility method for user input
- All have similar conditional logic for Samba (only configure if install is enabled)
- All set the same configuration structure: `self.config['components'][component_name] = value`

**Differences:**
- **Standard/Development**: Nearly identical flow, just different header text and default values
- **Custom**: Shows current values first, then prompts for changes
- **Custom**: Has more complex menu-driven interface

### 2. User Creation Methods - Shared Patterns

**Common building blocks across all modes:**
- `_get_user_type()` - Get user source (local/existing/domain)
- `_get_username()` - Get username with optional domain prefix
- `_confirm_domain_format()` - Ask about DOMAIN\ prefix
- User data structure creation with same fields: `name`, `source`, `account_type`, `groups`, `shell`, `home_directory`, `create_home`

**Shared user creation pattern:**
```python
user = {
    'name': username,
    'source': user_type,
    'account_type': account_type,
    'groups': {'primary': primary_group, 'secondary': secondary_groups},
    'shell': shell,
    'home_directory': home_dir,
    'create_home': create_home
}
```

### 3. Group Creation Methods - Similar Infrastructure

**Common patterns:**
- All use the same group data structure: `{'description': str, 'gid': int}`
- All use `_confirm()` for user input
- All validate group names and GIDs
- All show existing groups before adding new ones

## Proposed Unified Architecture

### **Core Philosophy**
All three modes follow the same fundamental pattern:
1. **Setup** → 2. **Configure Components** → 3. **Manage Groups** → 4. **Manage Users** → 5. **Configure Paths** → 6. **Finalize**

The key difference is **data source** and **interaction style**:
- **Dev**: Minimal defaults + simple prompts
- **Standard**: Template-driven + production defaults  
- **Custom**: Interactive builders + full flexibility

### **Unified Building Blocks**

```python
class ConfigWizard:
    # === UNIFIED FLOW CONTROL ===
    def _run_mode_unified(self, mode, accept_defaults_option=True):
        """Universal flow handler for all modes"""
        
        # 1. Setup phase
        self._setup_mode_defaults(mode)
        
        # 2. Choice point (if applicable)
        if accept_defaults_option:
            use_defaults = self._confirm(f"Accept all {mode} defaults?", True)
            if use_defaults:
                return self._apply_mode_defaults_complete(mode)
        
        # 3. Step-by-step configuration
        self._configure_components_unified(mode)
        self._configure_groups_unified(mode) 
        self._configure_users_unified(mode)
        self._configure_paths_unified(mode)
        
        # 4. Finalize
        return self._build_complete_config()
    
    # === UNIFIED COMPONENT CONFIGURATION ===
    def _configure_components_unified(self, mode):
        """Single component config method for all modes"""
        headers = {
            'simple': "=== Development Component Configuration ===",
            'standard': "=== Production Component Configuration ===",
            'custom': "--- Component Configuration ---"
        }
        
        defaults = self._get_component_defaults(mode)
        interactive = (mode == 'custom')
        
        if interactive:
            self._show_current_components()
            
        # Unified component flow
        for component in ['install_samba', 'configure_samba', 'install_acl', 
                         'configure_users_groups', 'configure_firewall']:
            self._configure_single_component(component, defaults.get(component), interactive)
    
    # === UNIFIED GROUP MANAGEMENT ===
    def _configure_groups_unified(self, mode):
        """Single group config method for all modes"""
        if mode == 'simple':
            self.config['groups'].update(get_development_admin_group())
        elif mode == 'standard':
            self._create_standard_groups()  # Uses standard_configs import
        elif mode == 'custom':
            self._manage_groups_interactive()
    
    # === UNIFIED USER MANAGEMENT ===  
    def _configure_users_unified(self, mode):
        """Single user config method for all modes"""
        if mode == 'simple':
            self._create_default_admin_user()
        elif mode == 'standard':
            self._create_users_from_templates(mode)
        elif mode == 'custom':
            self._manage_users_interactive()
    
    # === UNIFIED PATH CONFIGURATION ===
    def _configure_paths_unified(self, mode):
        """Single path config method for all modes"""
        if mode == 'simple':
            self._configure_development_paths()
        elif mode == 'standard':
            self._configure_standard_paths()
        elif mode == 'custom':
            self._configure_paths_interactive()
```

### **Key Benefits of This Design**

1. **Consistent User Experience**: All modes have the same step sequence and prompting patterns
2. **Code Reuse**: Eliminates near-duplicate methods like `_development_mode_components` vs `_standard_mode_components`
3. **Maintainability**: Changes to flow logic only need to be made in one place
4. **Extensibility**: Easy to add new modes or modify existing ones
5. **Testing**: Easier to test since the core flow is unified

### **Migration Strategy**

**Phase 1**: Create unified methods alongside existing ones
**Phase 2**: Update each mode to use unified methods one at a time
**Phase 3**: Remove old duplicate methods
**Phase 4**: Add enhanced custom mode features

### **Custom Mode Enhancement**

With the unified flow, custom mode becomes more powerful:
- **Linear Flow Option**: Step through components→groups→users→paths like other modes
- **Random Access**: Jump to any section via menu (current behavior)
- **Template Import**: Load standard/dev templates as starting points
- **Hybrid Workflow**: Start with template, then customize specific sections