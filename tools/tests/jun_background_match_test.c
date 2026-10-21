/* Actual renderer matcher against the stage's complete native mesh. */
#include "gpu_hd_texture_match.h"
#include <assert.h>
static uint16_t vram[512*1024];
int main(int argc,char **argv) {
    assert(argc==4);HdTextureMap map={0};
    FILE *f=fopen(argv[2],"rb");assert(f);
    assert(fread(vram,2,512*1024,f)==512*1024);fclose(f);
    assert(hd_map_load(&map,argv[1]) && map.count==10);
    f=fopen(argv[3],"rb");assert(f);
    uint32_t q[12];unsigned matches=0,water=0,excluded=0;
    while(fread(q,sizeof q,1,f)==1) {
        int u[3]={(int)q[5],(int)q[6],(int)q[7]};
        int v[3]={(int)q[8],(int)q[9],(int)q[10]};
        const HdTextureTile *t=hd_map_find(&map,vram,q[0],q[1],q[2],q[3],q[4],u,v);
        assert((t!=NULL)==(q[11]!=0));
        if(!t){excluded++;continue;}matches++;
        assert(t->kind==q[11]);
        if(t->kind==2)water++;
        unsigned pixel=t->y*1024+t->x,clut=t->cy*1024+t->cx;
        vram[pixel]^=1;++map.generation;
        assert(!hd_map_find(&map,vram,q[0],q[1],q[2],q[3],q[4],u,v));
        vram[pixel]^=1;vram[clut]^=1;++map.generation;
        assert(!hd_map_find(&map,vram,q[0],q[1],q[2],q[3],q[4],u,v));
        vram[clut]^=1;++map.generation;
        assert(hd_map_find(&map,vram,q[0],q[1],q[2],q[3],q[4],u,v));
    }
    assert(feof(f) && matches>=640 && water==4 && excluded>0);fclose(f);
    printf("Jun water: %u background triangles, %u distinct water tiles; %u unrelated queries excluded; pixel/palette guards passed\n",matches-water,water,excluded);
    hd_map_clear(&map);return 0;
}
