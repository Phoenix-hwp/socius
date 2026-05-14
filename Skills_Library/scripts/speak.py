#!/usr/bin/env python3
"""TTS 语音朗读 — 调用 Windows SAPI5 引擎，离线无网络依赖"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import pyttsx3

# 系统语音：慧慧（中文女声）
VOICE_ID = r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ZH-CN_HUIHUI_11.0'

# 语速：默认 200，150 更自然
RATE = 150

def speak(text: str):
    engine = pyttsx3.init()
    engine.setProperty('voice', VOICE_ID)
    engine.setProperty('rate', RATE)
    engine.say(text)
    engine.runAndWait()

if __name__ == '__main__':
    if len(sys.argv) >= 3 and sys.argv[1] == '--file':
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        text = sys.argv[1] if len(sys.argv) > 1 else ''

    if text:
        speak(text)
    else:
        print('Usage: python speak.py "<text>"')
        print('       python speak.py --file <path>')
