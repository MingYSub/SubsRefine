# SubsRefine

处理 TV 和 Web 的日文字幕。

支持 Python 3.11 及以上。

## 功能

- 支持读取 `ass` `srt` `vtt` 格式字幕
- 合并时间重复行
- 去除语气词
- 输出设置
  - 支持格式： `txt` `ass` `srt`
  - 行尾追加字符
  - 输出说话人
  - 停顿提示
- 全半角转换
  - 全角英数转为半角
  - 半角片假名转为全角
- 日文和西文之间添加空格
- 删除多余信息
  - 去除位置、颜色等信息
  - 删除未识别的外字
- 整理重复音节
- 批量转换

## 用法

### 命令行

```
usage: cli.py [-h] [--conf CONF] [--verbose] [-m {none,auto,force}] [-i] [-I] [-o OUTPUT_DIR] [-f {txt,srt,ass}]
              [-e OUTPUT_ENDING] [-s] [-S] [-p SHOW_PAUSE_TIP] [--numbers {skip,half,full,single_full}]
              [--letters {skip,half,full,single_full}] [-k] [-K] [-c] [-C] [--cjk-space-char CJK_SPACE_CHAR] [-r] [-R]
              [--repetition-connector REPETITION_CONNECTOR]
              path [path ...]

positional arguments:
  path                  Input files/directories

options:
  -h, --help            show this help message and exit
  --conf CONF           Configuration file path
  --verbose             Enable debug logging
  -m {none,auto,force}, --merge-strategy {none,auto,force}
                        Strategy for merging overlapping time-aligned lines
  -i                    Enable interjection filtering
  -I                    Disable interjection filtering
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        Directory to store output files
  -f {txt,srt,ass}, --output-format {txt,srt,ass}
                        Output file format (e.g., txt, srt, json)
  -e OUTPUT_ENDING, --output-ending OUTPUT_ENDING
                        String to append at the end of each line
  -s                    Enable speaker name display
  -S                    Disable speaker name display
  -p SHOW_PAUSE_TIP, --show-pause-tip SHOW_PAUSE_TIP
                        Show pause tip if pause exceeds this duration (in milliseconds)
  --numbers {skip,half,full,single_full}
                        Conversion strategy for full-width/half-width numbers
  --letters {skip,half,full,single_full}
                        Conversion strategy for full-width/half-width letters
  -k                    Enable conversion of half-width katakana to full-width
  -K                    Disable conversion of half-width katakana to full-width
  -c                    Enable automatic spacing between CJK and latin characters
  -C                    Disable automatic spacing between CJK and latin characters
  --cjk-space-char CJK_SPACE_CHAR
                        Custom space character to insert between CJK and latin characters
  -r                    Enable adjustment of repeated phrases
  -R                    Disable adjustment of repeated phrases
  --repetition-connector REPETITION_CONNECTOR
                        Connector used between repeated syllables
```

注意：

- 命令行参数会覆盖配置文件设置
- 默认配置文件路径：`工具目录/config.yaml`

### Windows GUI

暂无

## 配置文件

请见 [config.yaml](./config.yaml)

## 样例

### 原文（节选）

```
Dialogue: 0,0:08:07.37,0:08:10.44,Default,,0,0,0,,{\pos(340,1018)\c&H00ffff&}お父さんがいっぱいだー！\N
Dialogue: 0,0:08:10.44,0:08:14.04,Default,,0,0,0,,{\pos(620,898)\c&Hffff00&}意味が分からない\N
Dialogue: 0,0:08:10.44,0:08:14.04,Default,,0,0,0,,{\pos(620,1018)\c&Hffff00&}つまり えっと…\N
Dialogue: 0,0:08:14.04,0:08:19.11,Default,,0,0,0,,{\pos(340,898)\c&Hffff00&}姉は ﾖｼｭｱさんを流通用の段ﾎﾞｰﾙに\N
Dialogue: 0,0:08:14.04,0:08:19.11,Default,,0,0,0,,{\pos(340,1018)\c&Hffff00&}封印したってことでしょうか？\N
Dialogue: 0,0:08:19.11,0:08:22.72,Default,,0,0,0,,{\pos(620,898)}(清子)まあまあ\N
Dialogue: 0,0:08:19.11,0:08:22.72,Default,,0,0,0,,{\pos(620,1018)}今は楽しい歓迎会の場です\N
Dialogue: 0,0:08:22.72,0:08:26.22,Default,,0,0,0,,{\pos(940,898)}あとで考えましょ\N
Dialogue: 0,0:08:22.72,0:08:26.22,Default,,0,0,0,,{\pos(340,1018)\c&Hffff00&}お母さんは落ち着きすぎです！\N
Dialogue: 0,0:08:26.22,0:08:30.56,Default,,0,0,0,,{\pos(420,898)}それでは お父さんを入れて\N
Dialogue: 0,0:08:26.22,0:08:30.56,Default,,0,0,0,,{\pos(420,1018)}ｼｬｯﾌﾙｸｲｽﾞしたら面白そうです\N
Dialogue: 0,0:08:30.56,0:08:32.56,Default,,0,0,0,,{\pos(580,1018)}当てる自信ありです\N
Dialogue: 0,0:08:32.56,0:08:35.56,Default,,0,0,0,,{\pos(340,898)\c&Hffff00&}だとしても やめましょう\N
Dialogue: 0,0:08:32.56,0:08:35.56,Default,,0,0,0,,{\pos(1060,1018)}え～ でも\N
Dialogue: 0,0:08:35.56,0:08:38.06,Default,,0,0,0,,{\pos(580,898)}<頑張れシャミ子\N
Dialogue: 0,0:08:35.56,0:08:38.06,Default,,0,0,0,,{\pos(580,1018)}シャッフルクイズは>\N
Dialogue: 0,0:08:38.06,0:08:41.13,Default,,0,0,0,,{\pos(420,1018)}<当ててくれないと傷つくぞ>\N
```

### 处理后文本（默认设置）

```
お父さんがいっぱいだー！
意味が分からない　つまり　えっと…
姉は　ヨシュアさんを流通用の段ボールに　封印したってことでしょうか？
まあまあ　今は楽しい歓迎会の場です
あとで考えましょ
お母さんは落ち着きすぎです！
それでは　お父さんを入れて　シャッフルクイズしたら面白そうです
当てる自信ありです
だとしても　やめましょう
え～　でも
頑張れシャミ子　シャッフルクイズは
当ててくれないと傷つくぞ
```

## 开源许可

使用 [MIT](./LICENSE) 作为开源许可证。
