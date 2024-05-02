# Yambot

A bot that tracks listings on Yahoo! Auctions and Mercari and sends email updates.

## Usage

### Clone the repo
```bash
git clone --recurse-submodules https://github.com/zhecfy/yambot.git
```

### Install dependencies
```bash
cd yambot/
pip install -r mercari/requirements.txt
pip install -r Yoku/requirements.txt
```

### Setup email configurations
```bash
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

### Search options

#### (Mercari) Ambiguity Levels

Searching on mercari is sometimes quite painful. As long as an item's title and description contain all of the keywords, it may be shown in the search result. Sometimes completely different items with similar names flood the result. Sometimes the kanas in the keyword are incorrectly tokenized. The bot uses different ambiguity levels to determine which items are worth tracking.

- Level 1 (Absolutely Unique): track all items
- Level 2 (Unique): track items with full keyword in their title
- Level 3 (Ambiguous): search with supplemental keywords, track items with full keyword in their title

#### (Mercari) category_id

Set the カテゴリー on mercari and the number after `category_id=` in the URL. For example, the category_id for CD is 75.

#### (Yahoo! Auctions) auccat

Set the カテゴリ on yahoo auctions and the number after `auccat=` in the URL. For example, the auccat for Music is 22152.

### List current entries
```bash
python bot.py list
```

Also, take a look at the generated `track.json`. It's pretty human-readable.

### Modify the entries manually

More parameters are configurable for yahoo auctions, including `brand_id`, `aucmaxprice`, `s1`, `o1` and `fixed`. See [Yahoo! Auctions URL Parameters Guide (Unofficial)](Yoku/parameters.md) for details.

For example, if you want to set the `aucmaxprice` parameter of an entry, just add `"aucmaxprice": 1234,` in the JSON.

### Track manually
```bash
python bot.py track
```

### Track automatically

It depends on the system. For Linux, use crontab.

## Thanks

- [mercari](https://github.com/marvinody/mercari): a wrapper around mercari jp shopping site
- [Yoku](https://github.com/kokseen1/Yoku): A minimal Yahoo! Auctions scraper.
