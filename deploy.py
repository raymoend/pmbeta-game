#!/usr/bin/env python3
"""
Railway Deployment Helper for The Shattered Realm
Automates the deployment process and environment setup
"""

import os
import sys
import subprocess
import webbrowser
from pathlib import Path

def run_command(command, description=""):
    """Run a shell command and handle errors"""
    print(f"🔄 {description or command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(f"✅ {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def check_git_status():
    """Check if there are uncommitted changes"""
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
        return len(result.stdout.strip()) == 0
    except:
        return False

def main():
    print("🚀 The Shattered Realm - Railway Deployment Helper")
    print("=" * 50)
    
    # Check if we're in a git repository
    if not Path('.git').exists():
        print("❌ Not in a git repository. Please run from the project root.")
        sys.exit(1)
    
    # Check for uncommitted changes
    if not check_git_status():
        print("⚠️  You have uncommitted changes.")
        response = input("Do you want to commit and push them? (y/n): ")
        if response.lower() == 'y':
            run_command('git add .', "Staging all changes")
            commit_msg = input("Enter commit message (or press enter for default): ").strip()
            if not commit_msg:
                commit_msg = "Update for Railway deployment"
            run_command(f'git commit -m "{commit_msg}"', "Committing changes")
            run_command('git push origin main', "Pushing to GitHub")
        else:
            print("Please commit your changes before deploying.")
            sys.exit(1)
    
    print("\n🎯 Deployment Steps:")
    print("1. ✅ Code is committed and pushed to GitHub")
    print("2. 🔄 Opening Railway deployment...")
    
    # Open Railway in browser
    try:
        webbrowser.open('https://railway.app/new')
        print("✅ Railway opened in browser")
    except:
        print("⚠️  Please manually go to: https://railway.app/new")
    
    print("\n📋 Environment Variables to Set in Railway:")
    print("-" * 40)
    print(f"SECRET_KEY=(-&7j3zoor0g13+q&owifzw1y1x+!7zo#6+3^ix9@bf0*zv)(t")
    print("DJANGO_SETTINGS_MODULE=pmbeta.production_settings")
    print("DEBUG=False")
    print("MAPBOX_ACCESS_TOKEN=pk.your_actual_mapbox_token_here")
    print("\n⚠️  IMPORTANT: Replace 'pk.your_actual_mapbox_token_here' with your real MapBox token!")
    print("   Get it from: https://account.mapbox.com/access-tokens/")
    
    print("\n🎮 After deployment:")
    print("- Your game will be live at: https://your-project.railway.app")
    print("- Check the logs if anything goes wrong")
    print("- Initialize game data with monster spawning")
    
    print("\n🎉 The Shattered Realm is ready to deploy!")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
