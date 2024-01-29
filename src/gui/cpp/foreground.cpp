#include <windows.h>


extern "C" {
    __declspec(dllexport) int get_foreground_pid();
}


// Simple function to retrieve the PID of the current
// process displayed in the foreground of the computer.
// Uses Windows32 API. Returns -1 upon failure.
int get_foreground_pid() {
    HWND hwnd = GetForegroundWindow();
    if (hwnd == NULL) {
        // Something went wrong.
        return -1;
    }
    DWORD foreground_pid;
    GetWindowThreadProcessId(hwnd, &foreground_pid);
    return foreground_pid;
}
