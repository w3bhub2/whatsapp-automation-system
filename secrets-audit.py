#!/usr/bin/env python3
"""
Secrets Audit Script for W3BHub WhatsApp Automation System

This script implements the secrets audit requirement:
- Check for hardcoded credentials or keys in the repository
- Report any findings
"""

import os
import re
import subprocess
import json
from pathlib import Path

# Patterns to search for potential secrets
SECRET_PATTERNS = {
    'api_key': r'api[_-]?key["\s:=]*["\']?[\w\-]{20,}',
    'token': r'(token|access_token)["\s:=]*["\']?[\w\-]{20,}',
    'password': r'(password|passwd)["\s:=]*["\']?[\w\-@$!%*#?&]{8,}',
    'secret': r'(secret|private_key)["\s:=]*["\']?[\w\-]{20,}',
    'aws_key': r'(aws_access_key_id|aws_secret_access_key)["\s:=]*["\']?[A-Z0-9]{20,}',
    'google_api': r'(google_api_key)["\s:=]*["\']?[A-Za-z0-9\-_]{30,}',
    'telegram_token': r'(telegram_bot_token)["\s:=]*["\']?[0-9]{8,}:[A-Za-z0-9\-_]{30,}',
    'supabase_key': r'(supabase_key)["\s:=]*["\']?eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'
}

def run_git_grep(pattern):
    """Run git grep for a pattern"""
    try:
        # Use git grep to search for patterns in the repository
        result = subprocess.run(
            ['git', 'grep', '-i', '-n', pattern], 
            capture_output=True, 
            text=True,
            cwd=os.getcwd()
        )
        return result.stdout.split('\n') if result.returncode == 0 else []
    except Exception:
        # Fallback to simple file search if git grep fails
        matches = []
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and common build directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if file.endswith(('.py', '.js', '.json', '.env', '.yaml', '.yml', '.cfg', '.conf')):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                if re.search(pattern, line, re.IGNORECASE):
                                    matches.append(f"{filepath}:{line_num}:{line.strip()}")
                    except Exception:
                        continue
        return matches

def check_for_secrets():
    """Check repository for potential secrets"""
    findings = {}
    
    print("🔍 Scanning repository for potential secrets...")
    
    for pattern_name, pattern in SECRET_PATTERNS.items():
        print(f"  Checking for {pattern_name}...")
        matches = run_git_grep(pattern)
        
        if matches:
            findings[pattern_name] = matches
            print(f"    ⚠️  Found {len(matches)} potential {pattern_name}(s)")
        else:
            print(f"    ✅ No {pattern_name} found")
    
    return findings

def check_env_files():
    """Check for .env files that shouldn't be committed"""
    print("🔍 Checking for .env files...")
    env_files = []
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and common build directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            if file.startswith('.env') or file.endswith('.env'):
                filepath = os.path.join(root, file)
                env_files.append(filepath)
                print(f"  ⚠️  Found .env file: {filepath}")
    
    return env_files

def main():
    """Main function to audit secrets"""
    print("🔐 Secrets Audit Started")
    print("=" * 40)
    
    # Check for potential secrets in code
    secret_findings = check_for_secrets()
    
    # Check for .env files
    env_files = check_env_files()
    
    # Prepare report
    report = {
        'timestamp': __import__('datetime').datetime.now().isoformat(),
        'potential_secrets': secret_findings,
        'env_files': env_files,
        'summary': {
            'secrets_found': sum(len(matches) for matches in secret_findings.values()),
            'env_files_found': len(env_files)
        }
    }
    
    # Save report
    with open('diagnostics/secrets-audit.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 40)
    print("SECRETS AUDIT SUMMARY")
    print("=" * 40)
    print(f"Potential secrets found: {report['summary']['secrets_found']}")
    print(f".env files found: {report['summary']['env_files_found']}")
    
    if report['summary']['secrets_found'] > 0:
        print("\n⚠️  ACTION REQUIRED:")
        print("  Please review the diagnostics/secrets-audit.json file")
        print("  and remove any hardcoded secrets from the codebase.")
        print("  Use environment variables instead.")
    else:
        print("\n✅ No obvious secrets found in the codebase.")
    
    if report['summary']['env_files_found'] > 0:
        print("\n⚠️  WARNING:")
        print("  .env files should not be committed to the repository.")
        print("  Add them to .gitignore and use environment variables.")
    
    print("=" * 40)
    
    return report

if __name__ == "__main__":
    # Create diagnostics directory if it doesn't exist
    Path("diagnostics").mkdir(exist_ok=True)
    main()