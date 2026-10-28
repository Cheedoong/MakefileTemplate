#include <stdio.h>
#include "app/config.h"
#include "text.h"

int parse_value(void);
const char *format_value(int value);

int main(void) {
    int value = parse_value();
    printf("%s=%d\n", text_hello(), value);
    printf("%s\n", format_value(value));
    return 0;
}