void log_line(const char *who, int value);
int util_add(int a, int b);

int main() {
    log_line("alpha", util_add(1, 2));
    return 0;
}