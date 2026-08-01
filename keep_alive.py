#!/usr/bin/env python3
import sys
import time
import subprocess
import ctypes

def setup_x11():
    try:
        x11 = ctypes.cdll.LoadLibrary('libX11.so.6')
        xtest = ctypes.cdll.LoadLibrary('libXtst.so.6')
        
        # Configure ctypes signatures for 64-bit systems to avoid truncation segfaults
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XOpenDisplay.restype = ctypes.c_void_p
        
        x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        x11.XCloseDisplay.restype = ctypes.c_int
        
        x11.XWarpPointer.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int
        ]
        x11.XWarpPointer.restype = ctypes.c_int
        
        x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        x11.XStringToKeysym.restype = ctypes.c_ulong
        
        x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        
        x11.XFlush.argtypes = [ctypes.c_void_p]
        x11.XFlush.restype = ctypes.c_int
        
        xtest.XTestFakeKeyEvent.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong
        ]
        xtest.XTestFakeKeyEvent.restype = ctypes.c_int

        display = x11.XOpenDisplay(None)
        if display:
            return x11, xtest, display
    except Exception:
        pass
    return None, None, None

def run_keep_alive():
    duration = 3600  # 1 hour in seconds
    interval = 5     # 5 seconds
    steps = duration // interval
    
    x11, xtest, display = setup_x11()
    
    # Try importing pyautogui/pynput as secondary pythonic fallback
    pyautogui = None
    pynput_keyboard = None
    pynput_mouse = None
    
    if not x11:
        try:
            import pyautogui
        except ImportError:
            try:
                from pynput import keyboard, mouse
                pynput_keyboard = keyboard.Controller()
                pynput_mouse = mouse.Controller()
            except ImportError:
                pass

    print("Keep-alive script started. Running for 1 hour...")
    print(f"Implementation chosen: {'ctypes (X11)' if x11 else 'pyautogui' if pyautogui else 'pynput' if pynput_keyboard else 'xdotool (subprocess fallback)'}")
    
    wiggle = True
    
    for i in range(steps):
        try:
            # Determine offset for wiggling mouse
            dx = 5 if wiggle else -5
            dy = 5 if wiggle else -5
            wiggle = not wiggle
            
            # 1. Move Mouse & Type 'A'
            if x11 and xtest and display:
                # Move mouse relative
                x11.XWarpPointer(display, 0, 0, 0, 0, 0, 0, dx, dy)
                x11.XFlush(display)
                
                # Type 'A'
                keysym = x11.XStringToKeysym(b'A')
                keycode = x11.XKeysymToKeycode(display, keysym)
                if keycode:
                    shift_keycode = x11.XKeysymToKeycode(display, x11.XStringToKeysym(b'Shift_L'))
                    
                    # Shift Down
                    xtest.XTestFakeKeyEvent(display, shift_keycode, True, 0)
                    # 'A' Down & Up
                    xtest.XTestFakeKeyEvent(display, keycode, True, 0)
                    xtest.XTestFakeKeyEvent(display, keycode, False, 0)
                    # Shift Up
                    xtest.XTestFakeKeyEvent(display, shift_keycode, False, 0)
                    x11.XFlush(display)
            elif pyautogui:
                pyautogui.moveRel(dx, dy)
                pyautogui.write('A')
            elif pynput_keyboard and pynput_mouse:
                pynput_mouse.move(dx, dy)
                pynput_keyboard.press('A')
                pynput_keyboard.release('A')
            else:
                # Subprocess fallback to xdotool
                subprocess.run(['xdotool', 'mousemove_relative', '--', str(dx), str(dy)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(['xdotool', 'key', 'A'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
        except Exception as e:
            print(f"Step {i+1} action failed: {e}", file=sys.stderr)
            
        time.sleep(interval)

    # Clean up X11 display if opened
    if x11 and display:
        try:
            x11.XCloseDisplay(display)
        except Exception:
            pass
            
    print("Keep-alive script completed.")

if __name__ == '__main__':
    run_keep_alive()

