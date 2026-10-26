#include "rime_api.h"
// SPDX-License-Identifier: GPL-3.0-or-later
#include <iostream>
#include <fstream>
#include <string>
#include <cstring>
#include <chrono>
void rime_require_module_lua();


std::string quote(const char* p) {
  std::string out="\"";
  for (unsigned char c : std::string(p ? p : "")) {
    if(c=='"'||c=='\\') {out+='\\';out+=c;}
    else if(c=='\n')out+="\\n";
    else if(c=='\r')out+="\\r";
    else if(c=='\t')out+="\\t";
    else if(c>=32)out+=c;
  }
  return out+'"';
}
int main(int argc,char**argv){
  if(argc<3)return 2;
  rime_require_module_lua();

  auto api=rime_get_api();
  RIME_STRUCT(RimeTraits,t);
  const char* modules[]={"default","lua",nullptr};
  t.shared_data_dir=argv[2];
  t.user_data_dir=argv[1]; t.app_name="rime.loginput_probe";
  t.distribution_name="Loginput prototype tests";t.distribution_code_name="loginput_probe";
  t.distribution_version="0.1";t.modules=modules;t.min_log_level=2;t.log_dir="";
  api->setup(&t);api->initialize(&t);
  if(argc>3 && std::string(argv[3])=="--deploy"){
    api->start_maintenance(True);api->join_maintenance_thread();
  }
  auto sid=api->create_session();
  if(!api->select_schema(sid,"loginput_xiaohe")){std::cerr<<"schema selection failed\n";return 3;}
  auto sid1=sid; auto sid2=api->create_session();api->select_schema(sid2,"loginput_xiaohe");
  api->set_option(sid2,"ascii_mode",False);
  api->set_option(sid,"ascii_mode",False);
  std::string line;
  while(std::getline(std::cin,line)){
    auto pos=line.find('\t');
    std::string mode=pos==std::string::npos?"query":line.substr(0,pos);
    std::string input=pos==std::string::npos?line:line.substr(pos+1);
    if(mode=="session"){sid=input=="1" ? sid1 : sid2;continue;}
    if(mode=="schema") {
      if(!api->select_schema(sid, input.c_str())) return 4;
    }
    if(mode=="recreate") {
      bool first = sid == sid1;
      api->destroy_session(sid);
      sid=api->create_session();
      if(first) sid1=sid; else sid2=sid;
      if(!api->select_schema(sid,"loginput_xiaohe")) return 5;
      api->set_option(sid,"ascii_mode",False);
    }
    if(mode=="traditional") {
      api->set_option(sid, "traditional", input=="1" ? True : False);
    }
    if(mode!="step" && mode!="traditional" && mode!="schema" && mode!="recreate")api->clear_composition(sid);
    RIME_STRUCT(RimeCommit,old);if(api->get_commit(sid,&old))api->free_commit(&old);
    auto start=std::chrono::steady_clock::now();
    if(mode=="keys" || mode=="step")api->simulate_key_sequence(sid,input.c_str());
    else if(mode!="traditional" && mode!="schema" && mode!="recreate")api->set_input(sid,input.c_str());
    RIME_STRUCT(RimeContext,ctx);api->get_context(sid,&ctx);
    auto prop=[&](const char* name){char value[256]={};api->get_property(sid,name,value,sizeof(value));return std::string(value);};
    std::cout<<"{\"mode\":"<<quote(mode.c_str())<<",\"input\":"<<quote(input.c_str())
             <<",\"traditional\":"<<(api->get_option(sid,"traditional") ? "true" : "false")
             <<",\"raw\":"<<quote(api->get_input(sid))<<",\"preedit\":"<<quote(ctx.composition.preedit)
             <<",\"page_size\":"<<ctx.menu.page_size<<",\"visible\":"<<ctx.menu.num_candidates<<",\"logical_page\":"<<quote(prop("xh_pager_page").c_str())<<",\"has_next\":"<<quote(prop("xh_pager_next").c_str())<<",\"offset\":"<<quote(prop("xh_pager_offset").c_str())<<",\"page\":"<<ctx.menu.page_no<<",\"candidates\":[";
    RimeCandidateListIterator iter={};int count=0;
    if(api->candidate_list_begin(sid,&iter)){
      while(count<(mode=="all" ? 2000 : mode=="bulk" ? 6 : 60) && api->candidate_list_next(&iter)){
        if(count++)std::cout<<",";
        std::cout<<"{\"text\":"<<quote(iter.candidate.text)<<",\"comment\":"<<quote(iter.candidate.comment)<<"}";
      }api->candidate_list_end(&iter);
    }
    std::cout << "],\"labels\":[";
    for(int i=0;i<ctx.menu.num_candidates;++i){if(i)std::cout<<",";std::cout<<quote(ctx.select_labels ? ctx.select_labels[i] : (ctx.menu.select_keys ? std::string(1, ctx.menu.select_keys[i]).c_str() : "<none>"));}
    std::cout<<"]";
    api->free_context(&ctx);
    RIME_STRUCT(RimeCommit,commit);
    std::string committed;
    if(api->get_commit(sid,&commit)){committed=commit.text;api->free_commit(&commit);}
    auto micros=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
    std::cout<<",\"commit\":"<<quote(committed.c_str())<<",\"microseconds\":"<<micros<<"}"<<std::endl;
  }
  api->destroy_session(sid1);api->destroy_session(sid2);api->finalize();return 0;
}
