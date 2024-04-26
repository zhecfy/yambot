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

### Add a search entry
```bash
python bot.py add
```

Then the bot will prompt you to add a search entry interactively.

#### Ambiguity Levels

Searching on mercari is sometimes quite painful. As long as an item's title and description contain all of the keywords, it may be shown in the search result. Sometimes complete different items with similar names flood the result. Sometimes the kanas in the keyword are incorrectly tokenized. The bot uses different ambiguity levels to determine which items are worth tracking.

- Level 1 (Absolutely Unique): track all items
- Level 2 (Unique): track items with full keyword in their title
- Level 3 (Ambiguous): search with supplemental keywords, track items with full keyword in their title

#### Category ID

Same as the カテゴリー option on mercari.

### List current entries
```bash
python bot.py list
```

### Track manually
```bash
python bot.py track
```

### Track automatically

It depends on the system. For Linux, use crontab.

## Thanks

[Mercari Wrapper](https://github.com/marvinody/mercari)
