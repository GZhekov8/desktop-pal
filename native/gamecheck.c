/* Desktop Pal game check: tells the app whether a full-screen app is in front.
   Prints one line whenever the answer changes (and every 60 s):  <quns>|<fullscreen 0/1>|<exe name>
   quns = SHQueryUserNotificationState (3 = Direct3D full-screen game, 2 = busy/full-screen app, 4 = presentation).
   Exits when the app closes its stdin. Build: x86_64-w64-mingw32-gcc -O2 -s -municode -mwindows gamecheck.c -o gamecheck.exe -lshell32 */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <shellapi.h>
#include <stdio.h>
#include <wchar.h>

static DWORD WINAPI watchStdin(LPVOID p) {
  HANDLE in = GetStdHandle(STD_INPUT_HANDLE); char b[64]; DWORD n;
  while (ReadFile(in, b, sizeof b, &n, NULL) && n > 0) {}
  ExitProcess(0); return 0;
}

static void exeOf(HWND h, wchar_t *out, DWORD cap) {
  DWORD pid = 0; out[0] = 0; GetWindowThreadProcessId(h, &pid);
  HANDLE p = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
  if (!p) return;
  wchar_t full[MAX_PATH]; DWORD sz = MAX_PATH;
  if (QueryFullProcessImageNameW(p, 0, full, &sz)) { wchar_t *s = wcsrchr(full, L'\\'); wcsncpy(out, s ? s + 1 : full, cap - 1); out[cap - 1] = 0; }
  CloseHandle(p);
}

static int fullscreen(HWND h) {
  if (!h || !IsWindowVisible(h) || IsIconic(h)) return 0;
  wchar_t cls[64]; GetClassNameW(h, cls, 64);
  if (!wcscmp(cls, L"Progman") || !wcscmp(cls, L"WorkerW") || !wcscmp(cls, L"Shell_TrayWnd")) return 0;
  if (GetWindowLongW(h, GWL_STYLE) & WS_CAPTION) return 0;   /* a maximised normal window still has a title bar */
  RECT r; if (!GetWindowRect(h, &r)) return 0;
  MONITORINFO mi = { sizeof mi }; if (!GetMonitorInfoW(MonitorFromWindow(h, MONITOR_DEFAULTTONEAREST), &mi)) return 0;
  return r.left <= mi.rcMonitor.left && r.top <= mi.rcMonitor.top && r.right >= mi.rcMonitor.right && r.bottom >= mi.rcMonitor.bottom;
}

int wmain(void) {
  CreateThread(NULL, 0, watchStdin, NULL, 0, NULL);
  HANDLE out = GetStdHandle(STD_OUTPUT_HANDLE);
  char last[400] = "", line[400]; DWORD lastT = 0;
  for (;;) {
    QUERY_USER_NOTIFICATION_STATE q = 0; SHQueryUserNotificationState(&q);
    HWND h = GetForegroundWindow(); wchar_t exe[MAX_PATH]; exeOf(h, exe, MAX_PATH);
    char ex8[300]; WideCharToMultiByte(CP_UTF8, 0, exe, -1, ex8, sizeof ex8, NULL, NULL);
    snprintf(line, sizeof line, "%d|%d|%s\n", (int)q, fullscreen(h), ex8);
    DWORD now = GetTickCount();
    if (strcmp(line, last) || now - lastT > 60000) {
      DWORD w; if (!WriteFile(out, line, (DWORD)strlen(line), &w, NULL)) return 0;
      strcpy(last, line); lastT = now;
    }
    Sleep(2000);
  }
}
