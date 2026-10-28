#include <cstdio>

extern "C" int a(void);
extern "C" int upper(void);
int b(void);

int main() {
    printf("%d\n", a() + b() + upper());
    return 0;
}