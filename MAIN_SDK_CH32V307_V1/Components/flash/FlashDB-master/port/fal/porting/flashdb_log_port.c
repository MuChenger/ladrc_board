#include <stdarg.h>
#include <stdio.h>

int flashdb_printf(const char *fmt, ...)
{
    int ret;
    int i;
    int len;
    va_list args;
    char buf[256];

    va_start(args, fmt);
    len = vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    if (len < 0) {
        return len;
    }

    ret = 0;
    for (i = 0; (i < len) && (i < (int)sizeof(buf)); i++) {
        if (buf[i] == '\n') {
            putchar('\r');
            ret++;
        }
        putchar(buf[i]);
        ret++;
    }

    return ret;
}

