<p align="center"><img src="logo.png" width="96" alt="AI点歌"></p>

# AI点歌 · 高品质原曲与 AI 翻唱

适用于 **AstrBot** 的音乐插件：选歌听原曲、保存高品质音频，或使用自己的音色模型生成翻唱。

**版本：`v2.13.0.post2`** · **维护：stelliakkk** · **许可证：AGPL-3.0**

> 本仓库基于 [Matsuko / matsuko_cover v2.13.0](https://github.com/sdfsfsk/matsuko_cover) 定制，不是从零开发的独立原作。来源与修改见 [NOTICE.md](NOTICE.md)，原版文档见 [README_UPSTREAM.md](README_UPSTREAM.md)。

## 三条常用指令

| 指令 | 选择之后会收到什么 |
|---|---|
| `/听歌 晴天 周杰伦` | 原曲语音，在 QQ 对话中直接播放 |
| `/听歌文件 晴天 周杰伦` | 账号可用的高品质原始音频文件，例如 FLAC |
| `/翻唱 晴天 周杰伦` | 选择歌曲与音色后，收到 AI 翻唱语音 |

菜单支持回复序号、翻页和取消。旧命令 `/qqrvc` 仍然可用；`/翻唱帮助` 查看其他入口。可用 `/翻唱 晴天 6` 手动升高 6 个半音。

## 这个版本增加了什么

- **优先高品质取歌**：按照账号实际授权，优先母带/臻品 FLAC、普通 FLAC，再尝试高码率 OGG/MP3 和其他常规音质。
- **同曲目自动降级**：无权限、没有链接、下载失败、文件超限或音频格式不可读时，尝试该曲目的下一档音源。
- **文件保留原始音质**：取得 FLAC 就发送 `.flac`，不会先压成 MP3，也不会把低码率文件重新编码后冒充高品质。
- **安静模式**：隐藏开始、下载、分离、推理百分比及成功报告，保留必要菜单、成品和错误提示。
- **中文翻唱入口**：`/翻唱` 替代难记的英文命令，同时兼容旧指令。
- **兼容修复**：新版 QQ 音乐 `SongFileInfo/media_mid`、AstrBot `Node.uin` 类型，以及扫码过程中的空 Cookie 问题。

原版的 RVC、SVC-Fusion、SoulX-SVCVC、本地音频、模型管理、任务管理和 LLM 工具入口继续保留；具体可用性取决于你启用的后端与平台。

## 安装

**已验证：Windows + AstrBot 4.25.5 + Python 3.14.5。** 登录辅助脚本使用 Windows DPAPI，要求 Python 3.11 或以上；其他系统的账号登录迁移未在本定制版中验证。

### 用 ZIP 安装

1. 到 [Releases](https://github.com/stelliakkk/astrbot_plugin_matsuko_cover/releases) 下载插件 ZIP。
2. AstrBot 后台 → **AstrBot 插件 → 安装插件 → 上传本地 ZIP**，无需解压。
3. 等待依赖安装与加载，打开插件配置，按下方说明设置。

也可以在支持仓库地址安装的 AstrBot 版本中使用：

```text
https://github.com/stelliakkk/astrbot_plugin_matsuko_cover
```

**已装同名插件时**，AstrBot 4.25.5 的 ZIP 安装器会拒绝重复安装。本仓库保留原插件 ID；请先备份插件目录、对应配置和插件数据，再处理旧安装，不要同时加载两份同 ID 插件。

本仓库只包含插件代码。**FFmpeg、翻唱后端、音色模型和账号登录态需要单独准备**，不会随安装包附带。

## 先配好原曲听歌

1. 启用 QQ 音乐，建议 `default_api=qqmusic`。
2. 安装 FFmpeg，确保同目录有 FFprobe。将插件的 `original_song_ffmpeg_path` 填为本机 `ffmpeg.exe` 完整路径；也可留空并将工具加入 PATH。
3. 用运行 AstrBot 的 Python 环境完成 QQ 音乐登录。Windows 原生 venv 部署示例：

```powershell
# 在 AstrBot 根目录执行；其他部署方式请替换为实际解释器路径
.\venv\Scripts\python.exe .\data\plugins\astrbot_plugin_matsuko_cover\qqmusic_login.py --show
```

4. 使用手机 **QQ 扫一扫**，本人确认登录 QQ 音乐。终端显示 `LOGIN_SAVED` 后重载插件。
5. 发送 `/听歌文件 歌名` 验证文件效果，或 `/听歌 歌名` 验证语音效果。

凭据使用 Windows DPAPI 加密，保存到 `data/plugin_data/astrbot_plugin_matsuko_cover/`。它绑定当前 Windows 用户，复制到另一台电脑或另一用户下不能直接使用；二维码过期或登录失效时重新运行脚本。

只听原曲无需启动 RVC，也无需配置音色模型。

## 再配好 AI 翻唱

翻唱是独立的推理服务，不能只安装本插件就自动运行。

```text
QQ 音乐 → 授权音源下载 → 翻唱中间层 → 人声分离 / 变声 / 混音 → QQ 语音或文件
```

RVC 的典型部署由引擎和兼容中间层组成。已使用过的中间层为 [RVCSVC-API-amd](https://github.com/sdfsfsk/RVCSVC-API-amd)，后端安装与 GPU/CUDA 兼容性请按其项目说明处理。接口与参数需和本插件兼容，任意同名 RVC 服务并不一定能直接连接。

| 配置项 | 示例 / 作用 |
|---|---|
| `enable_rvc` | 开启 RVC；不使用的 SVC/SVCVC 可关闭 |
| `rvc_base_url` | `http://127.0.0.1:3333/`，填写中间层地址，保留结尾 `/` |
| `rvc_models_keywords` | 模型文件名与显示别名，可用 `/刷新rvc模型` 读取模型 |
| `default_api_type` | `rvc` |
| `default_model_index` | 从 `1` 开始的默认音色序号 |
| `f0_method` | RVC 示例值 `rmvpe` |
| `inference_timeout` | 按设备和歌曲长度设置，例如 `900` 秒 |

音色别名格式示例：

```text
模型.pth|||显示名称
```

音色模型及对应索引需自行准备并部署在后端。服务运行后，发送 `/翻唱 歌名`，按提示选歌、选音色即可。SVC-Fusion 和 SoulX-SVCVC 的参数及入口见 [原版说明](README_UPSTREAM.md)。

本地音频也可以先发给机器人，再在同一会话的有效缓存时间内使用 `/本地翻唱`；具体参数见 `/翻唱帮助`。

## 自然语言也可以翻唱

开启 `enable_smart_cover`，并确保 AstrBot 当前模型支持且允许调用插件工具后，可以说：

> 用当前女声音色翻唱周杰伦的《晴天》，完成后发语音给我。

模型实际调用 `smart_cover` 后才会开始处理。模型只回复文字时，可以直接使用 `/翻唱`。自然语言不保证每次都会触发工具；新增的 `/听歌` 与 `/听歌文件` 当前是指令入口，没有额外注册原曲播放 LLM 工具。

## 音质与输出说明

QQ 语音通道仍会转码。即使取到无损源，在语音气泡里播放也不等于无损；**需要保留音质时请用 `/听歌文件` 下载文件播放**。翻唱还会受到人声分离、变声模型与后端最终导出格式的影响。

高品质选择只在账号实际有权限、插件支持的常规立体声音源之间进行。专有加密编码和多声道专用档位不在这条取歌链中，不承诺所有曲目都能取得无损。文件可能为 `.flac`、`.mp3`、`.ogg`、`.m4a` 等真实格式。

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `quiet_mode` | `true` | 隐藏过程消息，不撤回历史消息或选择菜单 |
| `max_song_audio_size_mb` | `200` | 自动取歌上限，与本地音频上传限制分开 |
| `enable_send_file` | `false` | 翻唱结果是否在语音之外额外发送一份文件 |
| `timeout` | 以插件配置为准 | 菜单等待时间，可设置为 `60` 秒 |

`config.example.json` 是不含账号信息的参考配置，不会自动覆盖现有配置。群文件优先走 OneBot 群文件上传接口；不同 QQ 平台的文件能力可能不同。

## 常见问题

**只有文字回复，没有音频？** 检查 LLM 是否调用了工具，或改用 `/翻唱`；再检查后端、任务状态和错误提示。

**高品质取不到？** 检查登录状态、账号对具体曲目的播放权限、网络和文件上限。系统会尝试下一档，不会替换成其他歌曲。

**QQ 语音失败但收到了文件？** 插件会在语音发送失败时尝试文件兜底；以最后收到的文件和错误提示为准。

**更新会不会覆盖定制功能？** 本仓库的更新地址指向此定制仓库。手动从原上游安装或更新可能覆盖这些修改，升级前请备份数据。

## 自行构建安装包

构建只使用 Python 标准库，从明确的文件清单打包，不会收集账号、缓存、模型或本机环境：

```bash
python scripts/build_release.py
```

输出到 `dist/`：插件 ZIP 与 SHA-256 校验文件。ZIP 内含使用说明、许可证、版本记录和 `MANIFEST.json`。

## 验证范围与来源

post2 功能在本地通过过 15 项测试，覆盖音质排序、授权与下载降级、FLAC 字节保真、命令兼容和安静模式。还完成过实际授权 FLAC 下载、完整解码和 FLAC 输入的短片段 RVC 翻唱；原有整首翻唱语音已由使用者确认能够播放。

不同账号、平台和新部署环境仍需自行验证。仓库不包含歌曲、登录凭据、个人配置、模型和 GPU 后端。

- 原项目：[Matsuko / matsuko_cover](https://github.com/sdfsfsk/matsuko_cover)
- 更早的基础项目：[CCYellowStar2 / astrbot_plugin_rvc_svc](https://github.com/CCYellowStar2/astrbot_plugin_rvc_svc)
- 修改说明：[NOTICE.md](NOTICE.md) · 版本记录：[CHANGELOG.md](CHANGELOG.md)
- 许可证：[GNU AGPL v3](LICENSE)，保留原许可证与作者署名。
