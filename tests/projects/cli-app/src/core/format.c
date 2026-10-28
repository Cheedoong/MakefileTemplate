#include <stdio.h>
#include "app/config.h"

static char buffer[32];

const char *format_value(int value) {
    snprintf(buffer, sizeof buffer, "value:%d", value);
    return buffer;
}