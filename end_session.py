#!/usr/bin/env python3
"""
AMR-QTS Session End Script
===========================
Safely end a development session with Git commit, push, and change logging.

Usage:
    python end_session.py
    python end_session.py -m "feat: implement HMM regime detector"
    python end_session.py --no-push  # Commit but don't push
    python end_session.py --amend    # Amend last commit
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path
import argparse
from typing import List, Tuple


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


def get_current_branch() -> str:
    """Get the current Git branch name"""
    result = run_command(['git', 'branch', '--show-current'])
    return result.stdout.strip()


def get_git_status() -> Tuple[List[str], List[str], List[str]]:
    """Get lists of modified, new, and deleted files"""
    result = run_command(['git', 'status', '--porcelain'])
    
    modified = []
    new = []
    deleted = []
    
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        
        status = line[:2]
        filepath = line[3:]
        
        if status.strip() == 'M' or status.strip() == 'MM':
            modified.append(filepath)
        elif status.strip() == 'A' or status.strip() == '??':
            new.append(filepath)
        elif status.strip() == 'D':
            deleted.append(filepath)
        elif 'M' in status:
            modified.append(filepath)
    
    return modified, new, deleted


def display_changes():
    """Display all changed files in a formatted way"""
    print_header("CHANGES DETECTED")
    
    modified, new, deleted = get_git_status()
    
    if not (modified or new or deleted):
        print_info("No changes detected")
        return False
    
    if modified:
        print(f"\n{Colors.OKBLUE}{Colors.BOLD}Modified files ({len(modified)}):{Colors.ENDC}")
        for f in modified:
            print(f"  {Colors.OKCYAN}M{Colors.ENDC} {f}")
    
    if new:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}New files ({len(new)}):{Colors.ENDC}")
        for f in new:
            print(f"  {Colors.OKGREEN}A{Colors.ENDC} {f}")
    
    if deleted:
        print(f"\n{Colors.FAIL}{Colors.BOLD}Deleted files ({len(deleted)}):{Colors.ENDC}")
        for f in deleted:
            print(f"  {Colors.FAIL}D{Colors.ENDC} {f}")
    
    total = len(modified) + len(new) + len(deleted)
    print(f"\n{Colors.BOLD}Total: {total} file(s) changed{Colors.ENDC}")
    
    return True


def get_file_diff_stats(filepath: str) -> Tuple[int, int]:
    """Get the number of lines added and removed for a file"""
    try:
        result = run_command(['git', 'diff', '--cached', '--numstat', '--', filepath])
        if result.stdout.strip():
            parts = result.stdout.strip().split('\t')
            added = int(parts[0]) if parts[0] != '-' else 0
            removed = int(parts[1]) if parts[1] != '-' else 0
            return added, removed
        return 0, 0
    except:
        return 0, 0


def add_all_changes():
    """Stage all changes for commit"""
    print_info("Staging all changes...")
    
    try:
        run_command(['git', 'add', '-A'])
        print_success("All changes staged successfully")
        return True
    except subprocess.CalledProcessError:
        print_error("Failed to stage changes")
        return False


def generate_commit_message() -> str:
    """Generate a default commit message based on changes"""
    modified, new, deleted = get_git_status()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    parts = []
    if new:
        parts.append(f"add {len(new)} file(s)")
    if modified:
        parts.append(f"update {len(modified)} file(s)")
    if deleted:
        parts.append(f"delete {len(deleted)} file(s)")
    
    summary = ", ".join(parts)
    return f"chore: {summary} - session end {timestamp}"


def get_commit_message(provided_message: str = None, amend: bool = False) -> str:
    """Get commit message from user or use provided/default"""
    if amend:
        print_info("Amending previous commit...")
        return None  # Will use --amend flag
    
    if provided_message:
        return provided_message
    
    print_header("COMMIT MESSAGE")
    print_info("Suggested commit message types:")
    print(f"  {Colors.OKGREEN}feat:{Colors.ENDC}     New feature")
    print(f"  {Colors.OKBLUE}fix:{Colors.ENDC}      Bug fix")
    print(f"  {Colors.OKCYAN}docs:{Colors.ENDC}     Documentation")
    print(f"  {Colors.WARNING}refactor:{Colors.ENDC} Code refactoring")
    print(f"  {Colors.HEADER}test:{Colors.ENDC}     Adding tests")
    print(f"  {Colors.OKGREEN}chore:{Colors.ENDC}    Maintenance")
    
    default_msg = generate_commit_message()
    print(f"\n{Colors.BOLD}Default:{Colors.ENDC} {default_msg}")
    
    user_msg = input(f"\n{Colors.OKCYAN}Enter commit message (or press Enter for default): {Colors.ENDC}")
    
    return user_msg.strip() if user_msg.strip() else default_msg


def commit_changes(message: str = None, amend: bool = False) -> bool:
    """Commit staged changes"""
    print_info("Committing changes...")
    
    try:
        if amend:
            run_command(['git', 'commit', '--amend', '--no-edit'])
            print_success("Previous commit amended successfully")
        elif message:
            run_command(['git', 'commit', '-m', message])
            print_success(f"Committed with message: {message}")
        else:
            print_error("No commit message provided")
            return False
        
        return True
    except subprocess.CalledProcessError as e:
        print_error("Commit failed")
        return False


def push_changes(branch: str) -> bool:
    """Push commits to remote"""
    print_info(f"Pushing to origin/{branch}...")
    
    try:
        run_command(['git', 'push', 'origin', branch], capture=False)
        print_success(f"Successfully pushed to origin/{branch}")
        return True
    except subprocess.CalledProcessError:
        print_error("Push failed")
        print_info("You may need to:")
        print(f"  • Pull latest changes: {Colors.BOLD}git pull origin {branch}{Colors.ENDC}")
        print(f"  • Force push (careful!): {Colors.BOLD}git push -f origin {branch}{Colors.ENDC}")
        return False


def create_change_log():
    """Create a detailed change log for this session"""
    log_dir = Path('logs/sessions')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"session_end_{timestamp}.log"
    
    # Get commit info
    try:
        commit_hash = run_command(['git', 'rev-parse', 'HEAD']).stdout.strip()
        commit_msg = run_command(['git', 'log', '-1', '--pretty=%B']).stdout.strip()
    except:
        commit_hash = "N/A"
        commit_msg = "N/A"
    
    # Get change stats
    modified, new, deleted = get_git_status()
    
    with open(log_file, 'w') as f:
        f.write(f"Session End: {datetime.now()}\n")
        f.write(f"{'='*70}\n\n")
        f.write(f"Branch: {get_current_branch()}\n")
        f.write(f"Commit: {commit_hash}\n")
        f.write(f"Message: {commit_msg}\n\n")
        
        f.write(f"Changes Summary:\n")
        f.write(f"  Modified: {len(modified)} file(s)\n")
        f.write(f"  New:      {len(new)} file(s)\n")
        f.write(f"  Deleted:  {len(deleted)} file(s)\n")
        f.write(f"  Total:    {len(modified) + len(new) + len(deleted)} file(s)\n\n")
        
        if modified:
            f.write(f"Modified Files:\n")
            for file in modified:
                f.write(f"  - {file}\n")
        
        if new:
            f.write(f"\nNew Files:\n")
            for file in new:
                f.write(f"  + {file}\n")
        
        if deleted:
            f.write(f"\nDeleted Files:\n")
            for file in deleted:
                f.write(f"  - {file}\n")
        
        # Get detailed diff stats
        f.write(f"\n{'='*70}\n")
        f.write(f"Detailed Diff Stats:\n\n")
        try:
            diff_stats = run_command(['git', 'diff', 'HEAD~1', '--stat']).stdout
            f.write(diff_stats)
        except:
            f.write("(Diff stats not available)\n")
    
    print_success(f"Change log created: {log_file}")
    return log_file


def update_task_file():
    """Prompt user to update task.md if needed"""
    task_file = Path('docs/task.md')
    
    if not task_file.exists():
        task_file = Path('task.md')
    
    if not task_file.exists():
        print_warning("task.md not found - skipping task update prompt")
        return
    
    print_header("TASK UPDATE")
    print_info("Did you complete any tasks during this session?")
    print(f"Task file: {Colors.BOLD}{task_file}{Colors.ENDC}")
    
    response = input(f"\n{Colors.OKCYAN}Open task.md to update? (y/n): {Colors.ENDC}")
    
    if response.lower() == 'y':
        # Try to open with default editor
        editor = os.environ.get('EDITOR', 'nano')  # fallback to nano
        print_info(f"Opening with {editor}...")
        try:
            subprocess.run([editor, str(task_file)])
        except:
            print_warning(f"Could not open with {editor}. Please update manually: {task_file}")


def display_session_summary(log_file: Path):
    """Display final session summary"""
    print_header("SESSION SUMMARY")
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch = get_current_branch()
    
    print_info(f"Session ended: {current_time}")
    print_info(f"Branch: {branch}")
    print_info(f"Change log: {log_file}")
    
    # Get commit info
    try:
        commit_hash = run_command(['git', 'rev-parse', '--short', 'HEAD']).stdout.strip()
        print_success(f"Latest commit: {commit_hash}")
    except:
        pass


def main():
    parser = argparse.ArgumentParser(
        description='Safely end a development session for AMR-QTS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python end_session.py                           # Interactive mode
  python end_session.py -m "feat: add HMM model"  # With commit message
  python end_session.py --no-push                 # Commit but don't push
  python end_session.py --amend                   # Amend last commit
  python end_session.py --quick                   # Quick mode (no prompts)
        """
    )
    parser.add_argument('-m', '--message', help='Commit message')
    parser.add_argument('--no-push', action='store_true', help='Skip git push')
    parser.add_argument('--amend', action='store_true', help='Amend previous commit')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick mode with minimal prompts')
    parser.add_argument('--no-log', action='store_true', help='Skip change log creation')
    
    args = parser.parse_args()
    
    print_header("AMR-QTS SESSION END")
    
    # 1. Check if there are changes
    has_changes = display_changes()
    
    if not has_changes:
        print_info("No changes to commit. Exiting.")
        return
    
    # 2. Confirm before proceeding (unless quick mode)
    if not args.quick and not args.amend:
        response = input(f"\n{Colors.WARNING}Proceed with commit and push? (y/n): {Colors.ENDC}")
        if response.lower() != 'y':
            print_info("Session end cancelled")
            return
    
    # 3. Stage all changes
    if not add_all_changes():
        print_error("Failed to stage changes. Aborting.")
        sys.exit(1)
    
    # 4. Get commit message
    commit_msg = get_commit_message(args.message, args.amend)
    
    # 5. Commit changes
    if not commit_changes(commit_msg, args.amend):
        print_error("Commit failed. Aborting.")
        sys.exit(1)
    
    # 6. Create change log
    if not args.no_log:
        log_file = create_change_log()
    else:
        log_file = None
    
    # 7. Push to remote (unless --no-push)
    if not args.no_push:
        branch = get_current_branch()
        if not push_changes(branch):
            print_warning("Push failed, but changes are committed locally")
            print_info(f"You can push manually later: {Colors.BOLD}git push origin {branch}{Colors.ENDC}")
    else:
        print_info("Skipping push (--no-push flag)")
        print_info(f"Remember to push later: {Colors.BOLD}git push origin {get_current_branch()}{Colors.ENDC}")
    
    # 8. Update task file (unless quick mode)
    if not args.quick:
        update_task_file()
    
    # 9. Display summary
    if log_file:
        display_session_summary(log_file)
    
    print_header("SESSION COMPLETED")
    print_success("Development session ended successfully!")
    print_info("\nNext steps:")
    print(f"  • Changes are saved and pushed to Git")
    print(f"  • Run {Colors.BOLD}python start_session.py{Colors.ENDC} for next session")
    print(f"  • Check {Colors.BOLD}logs/sessions/{Colors.ENDC} for session logs\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Session end cancelled by user{Colors.ENDC}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
