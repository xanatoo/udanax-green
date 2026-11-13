/* Focused regression for the two indexes sharing one free-disk entry.
 * Include the historical implementation so its static indexes are inspectable.
 */
#include <assert.h>
#include <string.h>
#include "../green/be_source/multiloaf.c"

/* Only the exercised functions are linked from the historical module. */
int qerror(char *message) { (void)message; __builtin_trap(); return 0; }
int main(void)
{
    freediskentry one, two, three;
    int i;
    freediskconscell *node;
    one.partialdiskblocknumber = htonl(101);
    two.partialdiskblocknumber = htonl(102);
    three.partialdiskblocknumber = htonl(103);
    one.freespaceinloaf = htons(150);
    two.freespaceinloaf = htons(150);
    three.freespaceinloaf = htons(150);
    initincorealloctables();
    addtofreediskstructures(&one);
    addtofreediskstructures(&two);
    addtofreediskstructures(&three);
    /* Delete a middle list node, then head and tail. */
    deletefromfreediskstructures(fdhashtable[fdhash(102)]->stuff);
    assert(fdhashtable[fdhash(102)] == NULL);
    i = 0;
    for (node = fdorderedtable[3]; node; node = node->next) {
        assert(ntohl(node->stuff->partialdiskblocknumber) != 102);
        ++i;
    }
    assert(i == 2);
    deletefromfreediskstructures(fdhashtable[fdhash(103)]->stuff);
    deletefromfreediskstructures(fdhashtable[fdhash(101)]->stuff);
    assert(fdorderedtable[3] == NULL);
    assert(fdhashtable[fdhash(101)] == NULL);
    assert(fdhashtable[fdhash(103)] == NULL);
    return 0;
}
