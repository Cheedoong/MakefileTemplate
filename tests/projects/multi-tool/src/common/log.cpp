#include <cstdio>

void log_line(const char *who, int value) {
    std::printf("%s:%d\n", who, value);
}