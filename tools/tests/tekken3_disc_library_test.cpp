#include "../../src/tekken3_disc_library.h"
#include <cassert>
#include <iostream>
int main(int argc,char** argv) {
    assert(argc==2);
    auto root=std::filesystem::absolute(std::filesystem::u8path(argv[1]));
    std::filesystem::create_directories(root);
    const auto image=root/"Tekken 3 (USA).cue";
    {std::ofstream out(image);out<<"fixture - not a disc";}
    tekken3::DiscLibrary a;
    assert(a.load(root/"library.txt"));
    assert(a.attach(image.u8string()));
    assert(!a.attach((root/"."/"Tekken 3 (USA).cue").u8string()));
    assert(a.attach((root/u8"Missing é image.bin").u8string()));
    assert(a.entries[0].present && !a.entries[1].present);
    a.selected=a.entries[0].path;
    assert(a.save());
    tekken3::DiscLibrary b;assert(b.load(root/"library.txt"));
    assert(b.entries.size()==2 && b.entries[1].path==a.entries[1].path);
    assert(b.has_selection && b.selected==a.selected);
    assert(b.detach(0));assert(std::filesystem::exists(image));
    tekken3::DiscLibrary c;assert(c.load(root/"library.txt"));assert(c.entries.size()==1);
    assert(!c.detach(15));
    assert(c.detach(0));assert(c.selected.empty());
    assert(b.load(root/"library.txt") && b.has_selection && b.selected.empty() && b.entries.empty());
    {std::ofstream out(root/"broken.txt");out<<"DO NOT OVERWRITE";}
    assert(!c.load(root/"broken.txt"));assert(!c.save());
    std::ifstream in(root/"broken.txt");std::string text;std::getline(in,text);assert(text=="DO NOT OVERWRITE");
    std::cout<<"PASS library persistence, normalized duplicate paths, Unicode, missing files, nondestructive detach, corruption guard\n";
}
