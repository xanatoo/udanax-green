/* Check .backendrc numeric settings, including invalid input and bounds. */
#include <assert.h>
#include <stdio.h>
#include <unistd.h>
#include "../green/be_source/rcfile.c"

static void config(const char *text)
{
    FILE *f = fopen(".backendrc", "w");
    assert(f);
    assert(fputs(text, f) >= 0);
    assert(fclose(f) == 0);
    processrcfile();
    assert(unlink(".backendrc") == 0);
}

int main(void)
{
    char dir[] = "/tmp/udanax-rcfile-XXXXXX";
    assert(mkdtemp(dir));
    assert(chdir(dir) == 0);
    config("allocsize = 200000\nincrementalallocsize = 60000\nport = 9876\n");
    assert(allocsize == 200000);
    assert(incrementalallocsize == 60000);
    assert(portname == 9876);
    config("allocsize = 2\nincrementalallocsize = 1\n");
    assert(allocsize == 200000);
    assert(incrementalallocsize == 60000);
    assert(chdir("/") == 0);
    assert(rmdir(dir) == 0);
    return 0;
}
