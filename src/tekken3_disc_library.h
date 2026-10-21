#ifndef TEKKEN3_DISC_LIBRARY_H
#define TEKKEN3_DISC_LIBRARY_H
#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <sstream>
#include <string>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#endif

namespace tekken3 {
struct DiscEntry { std::string path; bool present=false; };
class DiscLibrary {
public:
    std::vector<DiscEntry> entries;
    std::string error;
    std::string selected;
    bool has_selection=false;
    std::filesystem::path file;
    static std::string normalize(const std::string& path) {
        if(path.empty())return {};
        std::error_code ec;
        auto p=std::filesystem::absolute(std::filesystem::u8path(path),ec);
        return ec?path:p.lexically_normal().generic_u8string();
    }
    static bool same(const std::string& a,const std::string& b) {
        auto x=normalize(a),y=normalize(b);
#ifdef _WIN32
        std::transform(x.begin(),x.end(),x.begin(),[](unsigned char c){return (char)std::tolower(c);});
        std::transform(y.begin(),y.end(),y.begin(),[](unsigned char c){return (char)std::tolower(c);});
#endif
        return x==y;
    }
    int find(const std::string& path) const {
        for(size_t i=0;i<entries.size();i++)if(same(entries[i].path,path))return (int)i;
        return -1;
    }
    bool attach(const std::string& path) {
        auto p=normalize(path);
        if(p.empty())return false;
        if(find(p)>=0)return false;
        if(p.size()>=512 || p.find_first_of("\r\n")!=std::string::npos || entries.size()>=64) {
            error="Cannot attach this path (512-byte path / 64-image limit).";return false;
        }
        std::error_code ec;
        entries.push_back({p,std::filesystem::is_regular_file(std::filesystem::u8path(p),ec)});
        return true;
    }
    void refresh() {
        for(auto& e:entries) {std::error_code ec;e.present=std::filesystem::is_regular_file(std::filesystem::u8path(e.path),ec);}
    }
    bool load(const std::filesystem::path& path) {
        file=path;entries.clear();error.clear();selected.clear();has_selection=false;
        std::error_code ec;
        if(!std::filesystem::exists(file,ec)) {
            if(ec)error="Disc library could not be accessed; existing file left untouched.";
            return !ec;
        }
        if(std::filesystem::file_size(file,ec)>131072 || ec) {
            error="Disc library could not be read; the existing file was left untouched.";return false;
        }
        std::ifstream in(file);std::string line;
        if(!std::getline(in,line) || (line!="TEKKEN3_DISC_LIBRARY 1" && line!="TEKKEN3_DISC_LIBRARY 2")) {
            error="Unrecognized disc library format; existing file left untouched.";return false;
        }
        if(line=="TEKKEN3_DISC_LIBRARY 2") {
            if(!std::getline(in,line)) {error="Missing disc library selection.";return false;}
            std::istringstream row(line);std::string tag;
            if(!(row>>tag>>std::quoted(selected)) || tag!="SELECTED") {error="Malformed disc library selection.";return false;}
            row>>std::ws;if(!row.eof()){error="Malformed disc library selection.";return false;}
            has_selection=true;
        }
        while(std::getline(in,line)) {
            std::istringstream row(line);std::string value;
            if(!(row>>std::quoted(value))) {error="Malformed disc library entry.";return false;}
            row>>std::ws;
            if(!row.eof()) {error="Malformed disc library entry.";return false;}
            attach(value);
        }
        if(in.bad())error="Disc library read failed.";
        if(has_selection && !selected.empty() && find(selected)<0)error="Selected image is not in the disc library.";
        return error.empty();
    }
    bool save() {
        if(!error.empty())return false; // Never overwrite a damaged/unreadable library.
        auto temp=file;temp+=".tmp";
        {std::ofstream out(temp,std::ios::trunc);out<<"TEKKEN3_DISC_LIBRARY 2\nSELECTED "<<std::quoted(selected)<<'\n';
         for(const auto& e:entries)out<<std::quoted(e.path)<<'\n';
         out.flush();if(!out){error="Could not save the disc library. Check folder permissions.";return false;}}
#ifdef _WIN32
        if(!MoveFileExW(temp.c_str(),file.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) {
            error="Could not replace the disc library; previous library preserved.";return false;
        }
#else
        std::error_code ec;std::filesystem::rename(temp,file,ec);
        if(ec){error="Could not replace the disc library; previous library preserved.";return false;}
#endif
        return true;
    }
    bool detach(size_t index) {
        if(index>=entries.size() || !error.empty())return false;
        auto previous=entries;auto old_selected=selected;
        bool active=same(entries[index].path,selected);entries.erase(entries.begin()+index);
        if(active)selected=entries.empty()?"":entries.front().path;
        if(save())return true;
        entries=std::move(previous);selected=std::move(old_selected);return false;
    }
};
}
#endif
