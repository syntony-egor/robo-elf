#!/bin/bash

# Stop Robo-Elf Discord Bot

cd /home/self-evolving-claude/robo-elf

if [ -f bot.pid ]; then
    PID=$(cat bot.pid)
    if ps -p $PID > /dev/null; then
        echo "Stopping bot (PID: $PID)..."
        kill $PID
        rm bot.pid
        echo "Bot stopped"
    else
        echo "Bot process not running"
        rm bot.pid
    fi
else
    echo "No PID file found. Bot may not be running."
    echo "Searching for bot process..."
    pkill -f "python3 bot.py"
    echo "Done"
fi
