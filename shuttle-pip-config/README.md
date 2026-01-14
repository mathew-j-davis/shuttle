# Shuttle Pip Config (Private)

This repository controls which version of Shuttle is deployed.

**This repo should be kept private** - it references the main shuttle repository.

## How It Works

```
VERSION file (0.2.0)
        │
        ▼
install.sh reads VERSION
        │
        ▼
pip install git+https://github.com/.../shuttle.git@v0.2.0#subdirectory=src/...
```

## Files

| File | Purpose |
|------|---------|
| `VERSION` | Single source of truth for version number |
| `install.sh` | Reads VERSION, installs from main repo |

## Usage

### Manual Installation

```bash
# Create venv first (if needed)
python3 -m venv /opt/shuttle/venv

# Run installer
./install.sh --venv /opt/shuttle/venv
```

### With Puppet

```puppet
# Clone this repo
vcsrepo { '/opt/shuttle/pip-config':
  ensure   => present,
  provider => git,
  source   => 'git@github.com:yourorg/shuttle-pip-config.git',
}

# Run install script
exec { 'shuttle-install':
  command => '/opt/shuttle/pip-config/install.sh --venv /opt/shuttle/venv',
  require => Vcsrepo['/opt/shuttle/pip-config'],
}
```

## Updating Version

1. Edit `VERSION` file: change `0.2.0` to `0.3.0`
2. Commit and push
3. Puppet will install new version on next run

## Version Must Match Tag in Main Repo

The VERSION file must match an existing git tag in the shuttle repo:

```bash
# In shuttle repo - create tag
git tag v0.2.0
git push origin v0.2.0

# In this repo - reference that tag
echo "0.2.0" > VERSION
```
