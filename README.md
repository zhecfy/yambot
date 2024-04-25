# Mercari bot

Never miss anything on your tracklist anymore.

## Usage

### Clone the repo
```bash
git clone --recurse-submodules https://github.com/zhecfy/mercari-bot.git
```

### Setup email configurations
```bash
cd mercari-bot/
cp email_config.json.example email_config.json
vim email_config.json
```
`MAIL_PASSWORD` is the SMTP login password for `MAIL_SENDER`.
For Gmail, [create and fill in an app password](https://support.google.com/mail/answer/185833).

### Add a search keyword
```bash
python bot.py add
```

### List current keywords
```bash
python bot.py list
```

### Track manually
```bash
python bot.py track
```

### Track automatically

Use crontab.

## Thanks

[Mercari Wrapper](https://github.com/marvinody/mercari)
