#!/usr/bin/env python3
"""
Simple script to run the Weaviate RAG Chat Application
"""

import subprocess
import sys
import os


def check_requirements():
    """Check if required packages are installed"""
    try:
        import streamlit
        import langchain
        import weaviate
        print("✅ All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please run: pip install -r requirements.txt")
        return False


def check_env_file():
    """Check if .env file exists"""
    if os.path.exists('.env'):
        print("✅ .env file found")
        return True
    else:
        print("⚠️  .env file not found. Please copy .env.example to .env and configure your API keys")
        return False


def main():
    print("🤖 Starting Weaviate RAG Chat Application...")
    print("=" * 50)

    # Check requirements
    if not check_requirements():
        sys.exit(1)

    # Check environment file
    check_env_file()

    print("\n🚀 Launching Streamlit application...")
    print("The application will open in your default browser")
    print("Press Ctrl+C to stop the application")
    print("=" * 50)

    # Run streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "LangGraph_app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error running application: {e}")


if __name__ == "__main__":
    main()