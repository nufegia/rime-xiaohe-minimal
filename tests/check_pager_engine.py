#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real librime/lua logical regression, without a native IME panel.
Compile engine_probe.cpp against librime and librime-lua, then pass its path and
an existing shared Rime data directory. All writes stay under --work-dir.
"""
from pathlib import Path
import argparse
import subprocess
import json
import sys

REPO = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--probe', type=Path, required=True)
p.add_argument('--shared-data', type=Path, required=True)
p.add_argument('--work-dir', type=Path, required=True)
args = p.parse_args()
PROBE = args.probe.resolve()
WORK = args.work_dir.resolve()
WORK.mkdir(parents=True, exist_ok=True)
if any(WORK.iterdir()):
    raise SystemExit('Use an empty --work-dir to protect existing data')

def run(root, commands, deploy=False):
    result = subprocess.run([str(PROBE), str(root), str(args.shared_data.resolve())]
                            + (['--deploy'] if deploy else []),
                            input='\n'.join(commands)+'\n' if commands else '',
                            capture_output=True, text=True, encoding='utf-8', check=True)
    rows = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    expected = sum(not cmd.startswith('session\t') for cmd in commands)
    assert len(rows) == expected, (len(rows), expected, result.stderr)
    return rows

def install(name, frontend):
    root = WORK / name
    subprocess.run([sys.executable, str(REPO/'scripts/manage.py'), 'install',
                    '--platform', frontend, '--user-dir', str(root)],
                   check=True, capture_output=True)
    return root

BASELINE = install('baseline', 'macos')
(BASELINE/'loginput_xiaohe.custom.yaml').write_text('patch: {}\n', encoding='utf-8')
run(BASELINE, [], deploy=True)
reports = []
for frontend in ('macos', 'windows', 'fcitx5', 'ibus'):
    STAGE = install(frontend, frontend)
    native = frontend != 'macos'
    second = '{Control_L}' if native else '{Super_L}'
    third = '{Control_R}' if native else '{Super_R}'
    run(STAGE, [], deploy=True)
    subprocess.run([sys.executable, str(REPO/'scripts/manage.py'), 'doctor',
                    '--platform', frontend, '--user-dir', str(STAGE)], check=True)
    codes=['hs','kr','ni','nihc','nihcuijp','o','oh','a','b','c','os','hsa']
    baselines=run(BASELINE,['all\t'+c for c in codes])
    base={c:r['candidates'] for c,r in zip(codes,baselines)}
    assert all(len(v)<2000 for v in base.values()),'Probe result was truncated'
    commands=[];checks=[]

    def add(command,expected,text='',page=None):
     commands.append(command);checks.append((expected,text,page))
    for code,all_candidates in base.items():
     pages=[all_candidates[:3]]+[all_candidates[i:i+10] for i in range(3,len(all_candidates),10)]
     add('keys\t'+code,pages[0],page=0)
     for page,window in enumerate(pages[1:],1):add('step\t{Tab}',window,page=page)
     add('step\t{Tab}',pages[-1],page=len(pages)-1)
     for page in range(len(pages)-2,-1,-1):add('step\t{Shift+Tab}',pages[page],page=page)
     add('step\t{Shift+Tab}',pages[0],page=0)
     # Every numbered selection on every complete page of two large candidate sets.
     if code in ['hs','kr']:
      for page,window in enumerate(pages):
       for i,item in enumerate(window):
        digit=str((i+1)%10)
        add('keys\t'+code+'{Tab}'*page+digit,[],text=item['text'])
    # first-screen invalid digit and incomplete final-page selection must not commit
    add('keys\ths0',base['hs'][:3],page=0)
    add('keys\tkr'+'{Tab}'*5+'0',base['kr'][43:53],page=5)
    # Editing and cancellation restart the logical pager.
    for seq,result_code in [('hs{Tab}a','hsa'),('hs{Tab}{BackSpace}','h'),('hs{Tab}{Escape}hs','hs')]:
     if result_code not in base:
      base[result_code]=run(BASELINE,['all\t'+result_code])[0]['candidates']
     add('keys\t'+seq,base[result_code][:3],page=0)
    add('keys\ths{Tab}{Left}',None,page=0)
    add('keys\ths{Page_Down}',base['hs'][3:13],page=1)
    add('keys\ths={minus}',base['hs'][:3],page=0)
    add('keys\ths{Down} ',[],text=base['hs'][1]['text'])
    add('keys\ths{Tab}{Down} ',[],text=base['hs'][4]['text'])
    add('keys\ths{Tab} ',[],text=base['hs'][3]['text'])
    add('keys\ths{Tab}'+second,[],text=base['hs'][4]['text'])
    add('keys\ths{Tab}'+third,[],text=base['hs'][5]['text'])
    add('keys\tnihcuijp'+second+' ',[],text='你好世界')
    add('keys\tnihcuijp'+third+' ',[],text='妳好世界')
    add('keys\toh ',[],text='🔴')
    add('keys\t1,',[],text=',')
    rows=run(STAGE,commands)
    failures=[]
    for index,(row,(expected,commit,page)) in enumerate(zip(rows,checks)):
     texts=[c['text'] for c in row['candidates']]
     wanted=None if expected is None else [c['text'] for c in expected]
     try:
      if wanted is not None:assert texts==wanted,(texts,wanted)
      assert row['commit']==commit,(row['commit'],commit)
      if page is not None:
       assert int(row['logical_page'])==page,(row['logical_page'],page)
       assert row['visible']==len(texts)
       assert len(texts)<= (3 if page==0 else 10)
       assert [c['comment'] for c in row['candidates']] == (['\u200b']*len(texts) if native or page==0 else [str((i+1)%10)+' ' for i in range(len(texts))])
       if native:
        assert row['labels'] == ([' ']*len(texts) if page==0 else [str((i+1)%10) for i in range(len(texts))]), row['labels']
     except AssertionError as e:failures.append({'index':index,'command':commands[index],'reason':str(e),'result':row})
    # Date values are dynamic: compare formatting rather than a minute-sensitive fixture.
    dates=run(STAGE,['keys\top','step\t{Tab}','step\t{Shift+Tab}','keys\top{Tab}1','keys\top{Tab}2'])
    assert len(dates[0]['candidates'])==3 and len(dates[1]['candidates'])==2
    assert len(dates[2]['candidates'])==3 and dates[2]['logical_page']=='0'
    assert dates[3]['commit'].count(':')==1 and ' ' in dates[3]['commit']
    assert '年' in dates[4]['commit'] and '分' in dates[4]['commit']
    assert all('\u200b' not in r['commit'] for r in rows+dates)
    assert not (STAGE/'loginput_xiaohe_smart.userdb').exists()
    sessions = run(STAGE, ['keys\ths{Tab}', 'session\t2', 'keys\tkr',
                           'session\t1', 'step\t', 'session\t2', 'step\t',
                           'step\t{Tab}', 'session\t1', 'step\t{Shift+Tab}',
                           'session\t2', 'step\t'])
    for row, page in zip(sessions, [1, 0, 1, 0, 1, 0, 1]):
        assert int(row['logical_page']) == page
        if native:
            labels = [' ']*len(row['candidates']) if page == 0 else [str((i+1)%10) for i in range(len(row['candidates']))]
            assert row['labels'] == labels, row
    assert not failures, failures[:3]
    # Native OpenCC filter: compare all logical traditional pages with an
    # unpaginated native-filter baseline, including post-conversion collisions.
    trad_codes = ['hs', 'hjyu', 'f', 'tf', 'favj', 'gjjk', 'nihcuijp']
    reference = run(BASELINE, ['traditional\t1'] + ['all\t'+c for c in trad_codes])[1:]
    trad_commands = ['traditional\t1']
    trad_checks = [None]
    for code, original in zip(trad_codes, reference):
        words = [c['text'] for c in original['candidates']]
        assert len(words) < 2000 and len(words) == len(set(words)), (code, words)
        pages = [words[:3]] + [words[i:i+10] for i in range(3, len(words), 10)]
        for page, window in enumerate(pages):
            trad_commands.append(('keys\t'+code) if page == 0 else 'step\t{Tab}')
            trad_checks.append((window, None, page))
        for page, window in enumerate(pages if code == 'hs' else []):
            for index in {0, len(window)-1}:
                if not window:
                    continue
                trad_commands.append('keys\t'+code+'{Tab}'*page+str((index+1)%10))
                trad_checks.append(([], window[index], None))
    for code, traditional_word in [('hjyu', '漢語'), ('tf', '頭髮'),
                                    ('favj', '發展'), ('gjjk', '乾淨'),
                                    ('favjvsgo', '發展中國'), ('oh', '🔴')]:
        trad_commands.append('keys\t'+code+' ')
        trad_checks.append(([], traditional_word, None))
    converted = run(STAGE, trad_commands)
    for row, expected in zip(converted, trad_checks):
        assert row['traditional'] is True
        if expected is None:
            continue
        words, committed, page = expected
        assert [c['text'] for c in row['candidates']] == words, row
        if committed is not None:
            assert row['commit'] == committed, row
        if page is not None:
            assert int(row['logical_page']) == page
            if native:
                assert row['labels'] == ([' ']*len(words) if page == 0 else [str((i+1)%10) for i in range(len(words))])
    switching = run(STAGE, ['traditional\t1', 'keys\ths{Tab}', 'traditional\t0',
                           'keys\thjyu', 'traditional\t1', 'step\t ',
                           'session\t2', 'keys\thjyu', 'session\t1',
                           'keys\thjyu', 'keys\top{Tab}2'])[1:]
    assert switching[1]['logical_page'] == '0' and switching[1]['visible'] == 3
    assert switching[2]['candidates'][0]['text'] == '汉语'
    assert switching[3]['candidates'][0]['text'] == '漢語'
    assert len({c['text'] for c in switching[3]['candidates']}) == 3
    assert switching[4]['commit'] == '漢語'
    assert switching[5]['traditional'] is False and switching[5]['candidates'][0]['text'] == '汉语'
    assert switching[6]['traditional'] is True and switching[6]['candidates'][0]['text'] == '漢語'
    assert '時' in switching[7]['commit'] and '分' in switching[7]['commit']
    assert all('\u200b' not in row['commit'] for row in converted+switching)
    assert not (STAGE/'loginput_xiaohe_smart.userdb').exists()
    menu = run(STAGE, ['keys\t{Control+grave}', 'step\t2'])
    option_index = next(i for i, c in enumerate(menu[1]['candidates']) if c['text'] == '简体')
    toggled = run(STAGE, ['keys\t{Control+grave}', 'step\t2',
                          'step\t'+str((option_index+1)%10), 'keys\thjyu '])
    assert toggled[-1]['traditional'] is True and toggled[-1]['commit'] == '漢語'
    traditional_cases = len(converted) + len(switching) + len(menu) + len(toggled)
    reports.append({'platform': frontend, 'cases': len(rows)+len(dates)+len(sessions)+traditional_cases,
                    'simplified_cases': len(rows)+len(dates)+len(sessions),
                    'traditional_cases': traditional_cases,
                    'failures': len(failures), 'native_ui_verified': False,
                    'cross_session_labels_isolated': True, 'no_learning_database': True, 'traditional_filter_verified': True,
                    'baseline_candidate_counts': {k: len(v) for k,v in base.items()},
                    'edit_prefix_only': ['h']})
(WORK/'report.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(reports, ensure_ascii=False, indent=2))
