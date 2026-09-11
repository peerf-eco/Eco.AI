---
name: eco-cli
description: Manage EcoOS components using eco cli - pull, install, update, find, and subscribe to components from the EcoOS Marketplace registry. Use when user requests Eco.Framework (EcoOS) component management operations, search, download, version updates, or marketplace interactions.
---

# Eco-CLI Component Management

This skill provides guidance for using the `eco` command-line tool to manage EcoOS components from the EcoOS Marketplace registry.

## Instructions

### Prerequisites Check

Before executing any eco-cli commands, verify:

1. **Authentication Status**: Check if user is authenticated
   - Look for `ECO_API_TOKEN` environment variable, or
   - Verify Cognito session exists in `.eco/session` file

2. **Environment Variables**: Confirm required paths are set:
   - `ECO_FRAMEWORK` - Development directory path
   - `ECO_FRAMEWORK_RT` - Runtime directory path (optional)

3. **AWS library**: check that aws fast download library 'libaws-crt-jni.*' (on Windows: 'aws-crt-jni.dll') is available:
- to use 'eco-cli' JAR version for JVM, user must enter: 'java -Djava.library.path=. -jar eco.jar'
- for Native-version ('eco-cli' without .jar) this 'libaws-crt-jni.dylib/.so/' (aws-crt-jni.dll) must be in same folder as 'eco-cli'.

### Command Execution Order

When helping users manage components, follow this workflow:

1. **Find/Search** - Locate components before pulling
2. **Pull/Get** - Download individual components to local environment
3. **Install/Setup** - Batch download all components from ecoPackage.json
4. **Update/Upgrade** - Keep components current
5. **Subscribe** - Register organization interest in components

### Authentication Commands

#### Login with Cognito (Interactive Password Prompt)
```bash
eco login -u user@email.com -p
```

#### Token-based Authentication (default, if token found)
```bash
# Using environment variable
export ECO_API_TOKEN=eco-your-48-char-hex-token-here

# Using command line option to force token use. if token found it is used by default
eco find -c CID123456789 -t eco-your-token-here
```

#### Force Session Authentication
```bash
eco find -c CID123456789 --session  # Use Cognito auth session only, has '-s' alias
```

### Component Discovery

#### Search by Name or Tags
```bash
eco find -u eco.list  # Searches both public and own organization workspace
```

#### Find by Component ID in UGUID format (CID)
```bash
eco find -c 58170CB18F454B6F96EBDE437E33987F
eco find -c 58170CB18F454B6F96EBDE437E33987F -p  # Public marketplace only filter
```

#### Find by Internal ID in Marketplace registry
```bash
eco find -i 9c9b3445-63d8-40de-a226-0475e1637a4e
```

### Component Download (Pull/Get)

#### Basic Pull with Auto-Detection
```bash
eco pull -c 58170CB18F454B6F96EBDE437E33987F -v 0.1
```
OS and architecture are auto-detected from the current system.

#### Pull with Explicit Platform
```bash
eco pull -c 58170CB18F454B6F96EBDE437E33987F -v 0.1 -o Windows -a x86-64   # '-o' stands for OS name, '-a' for CPU architecture
```

#### Pull to Development Directory
```bash
eco pull -c 58170CB18F454B6F96EBDE437E33987F -v 0.1 -d
```

#### Pull to Runtime Directory
```bash
eco pull -c 58170CB18F454B6F96EBDE437E33987F -v 0.1 -r
```

#### Pull Specific File by its Hash
```bash
eco pull -c 58170CB18F454B6F96EBDE437E33987F -h 32aa955e99d428ef4b8b558f6036889b98c6ea2713cfc56366a422319ca54ae5
```

#### Pull from public Published Marketplace registry only
```bash
eco pull -c 58170CB18F454B6F96EBDE437E33987F -v 0.1 -p  # '-p' stands for Published

### Component Update

The update command checks for newer versions of installed components and updates them from the EcoOS Marketplace registry.

#### Bulk Update (All Components)
```bash
eco update
```
Updates all components listed in `ecoPackage.json`. The command:
- Reads all components from `ecoPackage.json`
- Checks the marketplace for newer versions
- Shows which components have updates available
- Prompts for confirmation before updating

#### Update Specific Component by CID
```bash
eco update -c 58170CB18F454B6F96EBDE437E33987F
```

#### Update Specific Component by ID
```bash
eco update -i 9c9b3445-63d8-40de-a226-0475e1637a4e
```

#### Force Update (Overwrite Existing)
```bash
eco update -f                    # Force update all components
eco update -c 58170CB18F454B6F96EBDE437E33987F -f  # Force update specific component
```

#### Update in Development/Runtime Directory
```bash
eco update -d    # Update components in development directory (ECO_FRAMEWORK)
eco update -r    # Update components in runtime directory (ECO_FRAMEWORK_RT)
```

### Component Subscription

#### Subscribe to Component (optional, as autosubscribe is applied by default)
```bash
eco subscribe -c 58170CB18F454B6F96EBDE437E33987F
```

### Component Installation (Batch)

The `install` command downloads all components specified in an existing `ecoPackage.json` file. This is useful for setting up new environments or restoring component dependencies.

#### Basic Install from ecoPackage.json
```bash
eco install
```
Reads `ecoPackage.json` from current directory and installs all listed components.

#### Install to Development Directory
```bash
eco install -d
```
Installs components to the path specified in `ECO_FRAMEWORK` environment variable.

#### Install to Runtime Directory
```bash
eco install -r
```
Installs components to the path specified in `ECO_FRAMEWORK_RT` environment variable.

#### Install with Specific Platform
```bash
eco install -a amd64 -o linux
```
Installs components for a specific architecture and OS, overriding auto-detection.

#### Force Install (Skip Confirmation)
```bash
eco install -f
```
Overwrites existing components without prompting for confirmation.

### Environment Scanning

#### Scan Development Environment
```bash
eco scan -d
eco status --dev  # Alternative alias
```

#### Scan Runtime Environment
```bash
eco scan -r
eco status --rt  # Alternative alias
```

## Examples

### Example 1: New Project Setup

User wants to set up a new project with EcoOS components:

```bash
# Step 1: Authenticate
eco login -u developer@company.com -p

# Step 2: Search for required components forcing use of a login session auth
eco find -u interface-bus -s

# Step 3: Pull components to development directory
eco pull -c 00000000000000000000000042757331 -v 1.0.0 -d

# Step 4: Verify installation
eco scan -d
```

### Example 2: CI/CD Pipeline Integration

For automated pipelines using API tokens:

```bash
# Set authentication via environment
export ECO_API_TOKEN=eco-1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890

# Pull specific version for build
eco pull -c 58170CB18F454B6F96EBDE437E33987F -v 2.1.0 -o Linux -a x86-64

# Update specific component with forced overwrite
eco update -c 58170CB18F454B6F96EBDE437E33987F -f
```

### Example 3: Cross-Platform Component Management

User needs components for different platforms:

```bash
# Pull for Windows development
eco pull -c CID123456 -v 1.0.0 -o Windows -a x86-64 -d

# Pull for Linux runtime (for runtime only Dynamic libs allowed for download)
eco pull -c CID123456 -v 1.0.0 -o Linux -a x86-64 -r

# Pull for ARM64 embedded target
eco pull -c CID123456 -v 1.0.0 -o Linux -a arm64 -r
```

### Example 4: Component Update Workflow

```bash
# Check current installed components
eco scan -d

# Option A: Update all components at once
eco update

# Option B: Update specific component
eco find -c 58170CB18F454B6F96EBDE437E33987F
eco update -c 58170CB18F454B6F96EBDE437E33987F

# Force update without confirmation prompt
eco update -f
```

### Example 5: Batch Installation from ecoPackage.json

User needs to restore or set up a project with predefined dependencies:

```bash
# Step 1: Navigate to project directory with ecoPackage.json
cd /path/to/project

# Step 2: Verify ecoPackage.json exists
cat ecoPackage.json

# Step 3: Install all components listed in ecoPackage.json
eco install

# Step 4: Force install to overwrite existing (if needed)
eco install -f

# Step 5: Install for different target platform
eco install -a arm64 -o linux -r
```

## Best Practices

### Authentication

1. **Use API tokens for automation**: Set `ECO_API_TOKEN` environment variable for CI/CD pipelines, used by default
2. **Use interactive login for development**: The `-p` flag without value prompts for secure password entry. Use "-s/--session" in followup commands for login session auth
3. **Token format validation**: Tokens must follow format `eco-` followed by 48 hexadecimal characters and obtained in marketplace web-console

### Component Management

1. **Always scan before pulling**: Use `eco scan` to understand current environment state
2. **Use explicit versions**: Specify `-v` flag to ensure reproducible installations
3. **Prefer development directory for SDKs, Devkits or static builds**: Use `-d` flag for development components
4. **Use runtime directory for deployments**: Use `-r` flag for production-ready components - dynamic libraries

### Platform Specification

1. **Let CLI auto-detect when possible**: Omit `-o` and `-a` flags for current system
2. **Be explicit for cross-compilation**: Specify OS and architecture when targeting different platforms
3. **Supported OS values**: Windows, macOS, Linux (and aliases: win, osx, linux)
4. **Supported architectures**: x86_64, x86_32, arm64, arm32 (and aliases: amd64, rv64, etc.)

### Version Control

1. **Track ecoPackage.json**: Include in version control for reproducible builds
2. **Document component dependencies**: Review `dependencies` array in ecoPackage.json, may require to be brought at json root level
3. **Use semantic versioning**: Pull specific versions rather than always using latest

### Batch Installation

1. **Use install for project setup**: The `install` command is ideal for restoring all dependencies from an existing ecoPackage.json
2. **Create ecoPackage.json first**: Use `pull` commands for one or few individual components to build the initial ecoPackage.json, then add components' CIDs you need into "components" array attribute and use `install` for subsequent full install
3. **Prefer install over individual pulls**: When setting up a new environment, `eco install` is more efficient than pulling each component individually
4. **Use force flag cautiously**: The `-f` flag on install will overwrite all existing component files without confirmation

## Safety Protocol

### Destructive Operations Require Confirmation

Before executing any of the following operations, **ALWAYS** ask the user for explicit confirmation:

1. **Force Update (`-f` flag)**: Overwrites existing component files
   ```
   ⚠️ WARNING: This operation will overwrite existing files.
   Component: [CID]
   Destination: [path]
   
   Proceed? (yes/no)
   ```

2. **Force Install (`-f` flag)**: Overwrites existing components without prompting
   ```
   ⚠️ WARNING: Force install will overwrite existing component files.
   All components in ecoPackage.json will be reinstalled.
   
   Proceed? (yes/no)
   ```

3. **Pull to existing directory**: May overwrite existing components
   ```
   ⚠️ WARNING: Component [name] already exists at [path].
   This pull operation may overwrite existing files.
   
   Continue? (yes/no)
   ```

4. **Subscribe to component**: Creates organizational binding
   ```
   ℹ️ INFO: This will subscribe your organization to component [CID].
   This creates a subscription record in the marketplace.
   
   Proceed? (yes/no)
   ```

### Pre-Execution Checklist

Before running destructive commands, verify:

- [ ] User has confirmed the operation
- [ ] Correct component CID is specified
- [ ] Target directory is intended destination
- [ ] Version number is correct (if specified)
- [ ] Platform settings match target environment

### Error Recovery

If an operation fails:

1. Check authentication status: `eco scan`
2. Verify component exists: `eco find -c [CID]`
3. Check environment variables are set correctly
4. Review `.eco/session` file for valid tokens
5. Examine `ecoPackage.json` for component state

## Token Format Reference

Valid API token format:
```
eco-[48 hexadecimal characters]
```

Example valid tokens:
- `eco-1a2b3c4d5e6f7890abcdef1234567890abcdef1234567890`
- `eco-ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890` (case-insensitive)

## ecoPackage.json Structure

The CLI maintains this file in component directories:

```json
{
  "name": "my-package",
  "description": "Generated by Marketplace",
  "version": "1.0.0",
  "components": [
    {
      "name": "ComponentName",
      "cid": "COMPONENT_ID_HERE",
      "dependencies": []
    }
  ],
  "repositories": []
}
```

## Command Aliases Quick Reference

| Primary Command | Aliases |
|-----------------|---------|
| `scan` | `info`, `status` |
| `pull` | `get` |
| `update` | `upgrade` |
| `find` | `search` |
| `subscribe` | `sub` |
| `install` | `setup` |

## Exit Codes

- `0`: Success
- `1`: General error (authentication, network, etc.)
- `2`: Invalid arguments
- `3`: Component not found
- `4`: Permission denied

## Troubleshooting

### Authentication Issues

```bash
# Check current session
eco scan

# Re-authenticate (60 min login session TTL)
eco login -u user@email.com -p

# Verify token format
echo $ECO_API_TOKEN  # Should start with "eco-"
```

### Component Not Found

```bash
# Search
eco find -c CID123456


### Path Issues

```bash
# Verify environment variables
echo $ECO_FRAMEWORK
echo $ECO_FRAMEWORK_RT

# Check session file
cat .eco/session
```
