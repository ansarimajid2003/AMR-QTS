#!/usr/bin/env python3
"""
AMR-QTS Session Start Script
=============================
Safely start a development session with Git sync and context loading.

Usage:
    python start_session.py
    python start_session.py --branch feature/new-module
    python start_session.py --no-pull  # Skip git pull
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
import argparse


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(message: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{message.center(70)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*70}{Colors.ENDC}\n")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def run_command(command: list, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return result"""
    try:
        if capture:
            result = subprocess.run(
                command,
                check=check,
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(command, check=check)
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed: {' '.join(command)}")
        if capture and e.stderr:
            print_error(f"Error: {e.stderr}")
        raise


def check_git_repo() -> bool:
    """Check if current directory is a Git repository"""
    try:
        run_command(['git', 'rev-parse', '--git-dir'])
        return True
    except subprocess.CalledProcessError:
        return False


def get_current_branch() -> str:
    """Get the current Git branch name"""
    result = run_command(['git', 'branch', '--show-current'])
    return result.stdout.strip()


def check_uncommitted_changes() -> tuple[bool, str]:
    """Check if there are uncommitted changes"""
    result = run_command(['git', 'status', '--porcelain'])
    has_changes = bool(result.stdout.strip())
    return has_changes, result.stdout


def stash_changes() -> bool:
    """Stash any uncommitted changes"""
    try:
        result = run_command(['git', 'stash', 'push', '-m', f'Auto-stash before session start at {datetime.now()}'])
        return 'No local changes to save' not in result.stdout
    except subprocess.CalledProcessError:
        return False


def pull_latest(branch: str) -> bool:
    """Pull latest changes from remote"""
    try:
        print_info(f"Pulling latest changes from origin/{branch}...")
        result = run_command(['git', 'pull', 'origin', branch], capture=False)
        return True
    except subprocess.CalledProcessError:
        print_warning("Pull failed - you may need to resolve conflicts")
        return False


def pop_stash():
    """Pop the most recent stash"""
    try:
        print_info("Restoring your previous changes...")
        run_command(['git', 'stash', 'pop'])
        print_success("Previous changes restored")
    except subprocess.CalledProcessError:
        print_warning("Could not restore stashed changes - check 'git stash list'")


def display_project_context():
    """Display the PROJECT_CONTEXT.md file"""
    context_file = Path('docs/PROJECT_CONTEXT.md')
    
    if not context_file.exists():
        # Try alternate location
        context_file = Path('PROJECT_CONTEXT.md')
    
    if not context_file.exists():
        print_warning("PROJECT_CONTEXT.md not found - skipping context display")
        return
    
    print_header("PROJECT CONTEXT")
    
    with open(context_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract and display key sections
    lines = content.split('\n')
    in_section = False
    section_count = 0
    max_sections = 5  # Display first 5 sections
    
    for line in lines:
        # Headers
        if line.startswith('## '):
            if section_count >= max_sections:
                break
            in_section = True
            section_count += 1
            print(f"\n{Colors.OKBLUE}{Colors.BOLD}{line}{Colors.ENDC}")
        elif line.startswith('### ') and in_section:
            print(f"{Colors.OKCYAN}{line}{Colors.ENDC}")
        elif in_section and line.strip():
            # Only print first 3 lines of each section
            if section_count <= max_sections:
                print(f"  {line}")
    
    print(f"\n{Colors.OKGREEN}📖 Full context available in: {context_file}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}💡 Share this file with AI assistants for full project understanding{Colors.ENDC}")


def display_current_task():
    """Display current task from task.md"""
    task_file = Path('docs/task.md')
    
    if not task_file.exists():
        # Try alternate location
        task_file = Path('task.md')
    
    if not task_file.exists():
        print_warning("task.md not found - skipping task display")
        return
    
    print_header("CURRENT TASKS")
    
    with open(task_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find and display in-progress tasks
    current_phase = None
    for i, line in enumerate(lines):
        if line.startswith('## Phase'):
            current_phase = line.strip()
        elif '[ ]' in line or '[x]' not in line.lower():
            # Show incomplete tasks
            if current_phase:
                print(f"\n{Colors.OKBLUE}{current_phase}{Colors.ENDC}")
                current_phase = None  # Only print phase header once
            
            if '[ ]' in line:
                print(f"  {Colors.WARNING}⧖ {line.strip()}{Colors.ENDC}")
            elif line.strip().startswith('-'):
                print(f"  {line.strip()}")


def display_recent_commits(n: int = 3):
    """Display recent commits"""
    print_header(f"RECENT COMMITS (Last {n})")
    
    try:
        result = run_command([
            'git', 'log', 
            f'-{n}', 
            '--pretty=format:%C(yellow)%h%Creset - %C(cyan)%an%Creset - %C(green)%ar%Creset%n  %s%n'
        ])
        print(result.stdout)
    except subprocess.CalledProcessError:
        print_warning("Could not fetch recent commits")


def check_python_env():
    """Check if virtual environment is activated"""
    in_venv = sys.prefix != sys.base_prefix
    
    if in_venv:
        print_success(f"Virtual environment active: {sys.prefix}")
    else:
        print_warning("No virtual environment detected!")
        print_info("Consider activating venv: source venv/bin/activate (Linux/Mac) or venv\\Scripts\\activate (Windows)")


def display_session_info():
    """Display session information"""
    print_header("SESSION INFORMATION")
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print_info(f"Session started: {current_time}")
    print_info(f"Working directory: {os.getcwd()}")
    print_info(f"Python version: {sys.version.split()[0]}")
    
    try:
        branch = get_current_branch()
        print_info(f"Git branch: {branch}")
    except:
        print_warning("Could not determine Git branch")


def create_session_log():
    """Create a session log file"""
    log_dir = Path('logs/sessions')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"session_start_{timestamp}.log"
    
    with open(log_file, 'w') as f:
        f.write(f"Session Start: {datetime.now()}\n")
        f.write(f"Branch: {get_current_branch()}\n")
        f.write(f"Working Directory: {os.getcwd()}\n")
        f.write(f"Python: {sys.version}\n")
    
    print_success(f"Session log created: {log_file}")
    return log_file


def main():
    parser = argparse.ArgumentParser(
        description='Start a safe development session for AMR-QTS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_session.py                    # Start on current branch
  python start_session.py --branch feature/hmm   # Switch to branch
  python start_session.py --no-pull          # Skip git pull
  python start_session.py --quick            # Quick start (minimal output)
        """
    )
    parser.add_argument('--branch', '-b', help='Git branch to checkout')
    parser.add_argument('--no-pull', action='store_true', help='Skip git pull')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick start with minimal output')
    
    args = parser.parse_args()
    
    print_header("AMR-QTS SESSION START")
    
    # 1. Check Git repository
    if not check_git_repo():
        print_error("Not a Git repository! Run 'git init' first.")
        sys.exit(1)
    
    print_success("Git repository detected")
    
    # 2. Check for uncommitted changes
    has_changes, changes = check_uncommitted_changes()
    if has_changes:
        print_warning("You have uncommitted changes:")
        print(changes)
        
        response = input(f"\n{Colors.WARNING}Stash these changes before pulling? (y/n): {Colors.ENDC}")
        if response.lower() == 'y':
            if stash_changes():
                print_success("Changes stashed successfully")
                should_pop = True
            else:
                print_info("No changes to stash")
                should_pop = False
        else:
            print_info("Continuing without stashing...")
            should_pop = False
    else:
        print_success("Working directory is clean")
        should_pop = False
    
    # 3. Checkout branch if specified
    if args.branch:
        current = get_current_branch()
        if current != args.branch:
            print_info(f"Switching from {current} to {args.branch}...")
            try:
                run_command(['git', 'checkout', args.branch])
                print_success(f"Switched to branch: {args.branch}")
            except subprocess.CalledProcessError:
                print_error(f"Could not switch to branch: {args.branch}")
                sys.exit(1)
    
    # 4. Pull latest changes
    if not args.no_pull:
        current_branch = get_current_branch()
        if pull_latest(current_branch):
            print_success("Successfully pulled latest changes")
        else:
            print_warning("Pull had issues - review above")
    else:
        print_info("Skipping git pull (--no-pull flag)")
    
    # 5. Pop stash if we stashed earlier
    if should_pop:
        pop_stash()
    
    # 6. Display session information
    if not args.quick:
        display_session_info()
        check_python_env()
        
        # 7. Display project context
        display_project_context()
        
        # 8. Display current tasks
        display_current_task()
        
        # 9. Display recent commits
        display_recent_commits(3)
    
    # 10. Create session log
    log_file = create_session_log()
    
    print_header("SESSION READY")
    print_success("Development session started successfully!")
    print_info("\nQuick tips:")
    print(f"  • Run {Colors.BOLD}python end_session.py{Colors.ENDC} when done")
    print(f"  • Read {Colors.BOLD}docs/PROJECT_CONTEXT.md{Colors.ENDC} for AI assistants")
    print(f"  • Check {Colors.BOLD}docs/task.md{Colors.ENDC} for current tasks")
    print(f"  • Session log: {Colors.BOLD}{log_file}{Colors.ENDC}\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Session start cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
