void log_line(const char *who, int value);
int util_add(int a, int b);

int main() {
    log_line("beta", util_add(3, 4));
    return 0;
}