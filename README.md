# PT 站点自动签到机器人

这是一个用于 PT (Private Tracker) 站点自动签到的 Python 脚本，可以帮助你自动完成每日签到任务。

该项目改自[madwind/flexget_qbittorrent_mod](https://github.com/madwind/flexget_qbittorrent_mod)，由大模型gemini驱动优化

## 特性

- 支持多种 PT 站点。
- 支持通过 Telegram 发送签到结果通知。
- 可通过 `config.yml` 文件灵活配置。
- 支持并发执行签到任务。

## 安装

1.  克隆本项目到本地。
2.  安装所需的依赖库：
    ```bash
    pip install -r requirements.txt
    ```

## 配置

1.  将 `config_example.yml` 文件复制并重命名为 `config.yml`。
2.  打开 `config.yml` 文件进行编辑。

### 主要配置项

-   `user-agent`: (可选) 全局 User-Agent，默认为空。
-   `cookie_backup`: (可选) 是否备份 Cookie，默认为 `True`。
-   `aipocr`: (可选) 百度 OCR 相关配置，用于需要验证码的站点。
-   `sites`: **(必需)** 在这里配置你需要签到的站点。
    -   每个站点的键名是站点的 `site_name` (例如 `hdchina`)。
    -   `use_cookie_cloud`: 是否从CookieCloud获取cookie，默认为 `True`。
    -   `cookie`：比CookieCloud优先级级低。
-   `notification`: (可选) 配置消息通知。
    -   目前仅支持 `telegram`。
    -   需要提供 `bot_token` 和 `chat_id`。


## 运行

配置完成后，直接运行主脚本即可：

```bash
python pt_checkin.py
```

脚本会自动读取 `config.yml` 配置，并为所有已配置的站点执行签到任务。

## 注意事项

-   请务必保护好你的 `config.yml` 文件，其中包含你的个人敏感信息。
-   部分站点可能需要额外的配置项，请参考 `config_example.yml` 中的注释。
