#!/bin/bash

# Start Robo-Elf Discord Bot in background

cd /home/self-evolving-claude/robo-elf

# Create logs directory if it doesn't exist
mkdir -p logs

# Start bot in background, redirecting output to log file
nohup /usr/bin/python3 bot.py >> logs/bot.log 2>&1 &

# Save PID to file
echo $! > bot.pid

echo "Bot started with PID $(cat bot.pid)"
echo "Logs: logs/bot.log"
