#!/usr/bin/env python3
"""
Setup script for AMR-QTS session management tools
==================================================
Run this once to configure your session management scripts.

Usage:
    python setup_session_tools.py
"""

import os
import sys
import stat
from pathlib import Path
import platform


def print_header(message: str):
    """Print a formatted header"""
    print(f"\n{'='*70}")
    print(f"{message.center(70)}")
    print(f"{'='*70}\n")


def print_success(message: str):
    """Print success message"""
    print(f"✓ {message}")


def print_info(message: str):
    """Print info message"""
    print(f"ℹ {message}")


def print_warning(message: str):
    """Print warning message"""
    print(f"⚠ {message}")


def print_error(message: str):
    """Print error message"""
    print(f"✗ {message}")


def make_executable(filepath: Path):
    """Make a file executable on Unix systems"""
    if platform.system() != 'Windows':
        current_permissions = os.stat(filepath).st_mode
        os.chmod(filepath, current_permissions | stat.S_IEXEC)


def create_logs_directory():
    """Create logs/sessions directory if it doesn't exist"""
    log_dir = Path('logs/sessions')
    
    if log_dir.exists():
        print_info(f"Logs directory already exists: {log_dir}")
    else:
        log_dir.mkdir(parents=True, exist_ok=True)
        print_success(f"Created logs directory: {log_dir}")


def check_git_config():
    """Check if Git is configured"""
    try:
        import subprocess
        
        # Check Git user name
        result = subprocess.run(
            ['git', 'config', 'user.name'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            print_warning("Git user.name not configured")
            print_info("Run: git config --global user.name 'Your Name'")
            return False
        
        # Check Git user email
        result = subprocess.run(
            ['git', 'config', 'user.email'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0 or not result.stdout.strip():
            print_warning("Git user.email not configured")
            print_info("Run: git config --global user.email 'your@email.com'")
            return False
        
        print_success("Git configuration verified")
        return True
        
    except FileNotFoundError:
        print_error("Git is not installed or not in PATH")
        return False


def create_gitignore_entry():
    """Add session logs to .gitignore if needed"""
    gitignore_path = Path('.gitignore')
    
    if not gitignore_path.exists():
        print_warning(".gitignore not found - skipping")
        return
    
    with open(gitignore_path, 'r') as f:
        content = f.read()
    
    if 'logs/sessions/' in content:
        print_info("Session logs already in .gitignore")
    else:
        print_info("Adding session logs to .gitignore...")
        with open(gitignore_path, 'a') as f:
            f.write('\n# Session logs (local audit trail)\n')
            f.write('logs/sessions/\n')
        print_success("Updated .gitignore")


def setup_scripts():
    """Make scripts executable and verify they exist"""
    scripts = [
        'start_session.py',
        'end_session.py'
    ]
    
    missing_scripts = []
    
    for script_name in scripts:
        script_path = Path(script_name)
        
        if not script_path.exists():
            missing_scripts.append(script_name)
            print_error(f"Script not found: {script_name}")
        else:
            # Make executable on Unix systems
            if platform.system() != 'Windows':
                make_executable(script_path)
                print_success(f"Made executable: {script_name}")
            else:
                print_success(f"Verified: {script_name}")
    
    if missing_scripts:
        print_error(f"\nMissing scripts: {', '.join(missing_scripts)}")
        print_info("Please ensure all session management scripts are in the project root")
        return False
    
    return True


def create_shell_aliases():
    """Suggest shell aliases for convenience"""
    print_header("OPTIONAL: Shell Aliases")
    
    print_info("You can add these aliases to your shell config for convenience:")
    print("\nFor Bash/Zsh (~/.bashrc or ~/.zshrc):")
    print("  alias start='python start_session.py'")
    print("  alias end='python end_session.py'")
    
    print("\nFor Fish (~/.config/fish/config.fish):")
    print("  alias start='python start_session.py'")
    print("  alias end='python end_session.py'")
    
    print("\nFor PowerShell (Microsoft.PowerShell_profile.ps1):")
    print("  function start { python start_session.py }")
    print("  function end { python end_session.py }")
    
    print("\nThen you can just run:")
    print("  start     # instead of python start_session.py")
    print("  end       # instead of python end_session.py")


def verify_python_version():
    """Check Python version"""
    version = sys.version_info
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python 3.8+ required, found {version.major}.{version.minor}")
        return False
    
    print_success(f"Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def create_test_log():
    """Create a test session log to verify setup"""
    from datetime import datetime
    
    log_dir = Path('logs/sessions')
    test_log = log_dir / 'setup_test.log'
    
    try:
        with open(test_log, 'w') as f:
            f.write(f"Session management setup test\n")
            f.write(f"Timestamp: {datetime.now()}\n")
            f.write(f"Setup successful!\n")
        
        print_success(f"Test log created: {test_log}")
        
        # Clean up test log
        test_log.unlink()
        print_info("Test log removed (cleanup)")
        
        return True
    except Exception as e:
        print_error(f"Could not create test log: {e}")
        return False


def display_usage_guide():
    """Display quick usage guide"""
    print_header("USAGE GUIDE")
    
    print("Start a session:")
    print("  python start_session.py")
    print("  python start_session.py --branch feature/name")
    print("  python start_session.py --quick")
    
    print("\nEnd a session:")
    print("  python end_session.py")
    print("  python end_session.py -m 'feat: your message'")
    print("  python end_session.py --no-push")
    
    print("\nFor detailed help:")
    print("  python start_session.py --help")
    print("  python end_session.py --help")
    print("  cat SESSION_MANAGEMENT.md")


def main():
    """Main setup routine"""
    print_header("AMR-QTS Session Management Setup")
    
    success = True
    
    # 1. Check Python version
    print("Checking Python version...")
    if not verify_python_version():
        success = False
    
    # 2. Check Git configuration
    print("\nChecking Git configuration...")
    if not check_git_config():
        print_warning("Please configure Git before using session management")
    
    # 3. Create logs directory
    print("\nSetting up logs directory...")
    create_logs_directory()
    
    # 4. Update .gitignore
    print("\nUpdating .gitignore...")
    create_gitignore_entry()
    
    # 5. Setup scripts
    print("\nSetting up scripts...")
    if not setup_scripts():
        success = False
    
    # 6. Test log creation
    print("\nTesting log creation...")
    if not create_test_log():
        print_warning("Log creation test failed - check permissions")
    
    # 7. Display shell aliases
    create_shell_aliases()
    
    # 8. Display usage guide
    display_usage_guide()
    
    # Final status
    print_header("SETUP COMPLETE" if success else "SETUP INCOMPLETE")
    
    if success:
        print_success("Session management tools are ready to use!")
        print_info("\nNext steps:")
        print("  1. Run: python start_session.py")
        print("  2. Do your work")
        print("  3. Run: python end_session.py")
        print("\nSee SESSION_MANAGEMENT.md for full documentation")
    else:
        print_error("Some setup steps failed - please review errors above")
        return 1
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
