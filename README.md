# Yambot

Track listings on Yahoo! Auctions and Mercari and get email updates.

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

Then yambot will prompt you to add a search entry interactively.

### Search options

#### Yambot's Ambiguity Levels for Mercari

Searching on mercari is sometimes quite painful. As long as an item's title and description contain all of the keywords, it may be shown in the search result. Sometimes completely different items with similar names flood the result. Sometimes the kanas in the keyword are incorrectly tokenized. Yambot uses different ambiguity levels to determine which items are worth tracking.

- Level 1 (Absolutely Unique): track all items
- Level 2 (Unique): track items with full keyword in their title
- Level 3 (Ambiguous): search with supplemental keywords, track items with full keyword in their title

#### Category of Mercari Items (`category_id`)

Set the カテゴリー on mercari and the number after `category_id=` in the URL. For example, the category_id for CD is 75.

List of integers, seperated with comma. Example: 694,695

#### Conditions of Mercari Items (`item_condition_id`)

- 1: 新品、未使用
- 2: 未使用に近い
- 3: 目立った傷や汚れなし
- 4: やや傷や汚れあり
- 5: 傷や汚れあり
- 6: 全体的に状態が悪い

List of integers, seperated with comma. Example: 3,4,6

#### Category of Yahoo! Auctions Items (`auccat`)

Set the カテゴリ on yahoo auctions and the number after `auccat=` in the URL. For example, the auccat for Music is 22152.

One integer.

#### Conditions of Yahoo! Auctions Items (`istatus`)

- 1: 未使用
- 2: 中古
- 3: 未使用に近い
- 4: 目立った傷や汚れなし
- 5: やや傷や汚れあり
- 6: 傷や汚れあり
- 7: 全体的に状態が悪い

List of integers, seperated with comma. Example: 3,4,6
Note: 2 is equivalent to 3,4,5,6,7

### List current entries
```bash
python bot.py list
```

Also, take a look at the generated `track.json`. It's pretty human-readable.

### Modify the entries manually

More parameters are configurable for yahoo auctions, including `brand_id`, `s1`, `o1` and `fixed`. See [Yahoo! Auctions URL Parameters Guide (Unofficial)](https://github.com/zhecfy/Yoku/blob/main/parameters.md) for details.

For example, if you want to set the `brand_id` parameter of an entry, just add `"brand_id": 101091,`.

### Track manually
```bash
python bot.py track
```

Or, to track a specific entry, give yambot its entry id:

```bash
python bot.py track --id=12
```

### Track automatically

It depends on the system. For Linux, use crontab.

### What does it track, exactly? When will I get notified?

For mercari listings, yambot tracks attibutes `price` and `status` ("On Sale" or "Sold Out" etc.) for each item.

For yahoo auction listings, yambot tracks attibutes `curr_price` and `bid_count` for each item.

Everytime yambot runs the track() function, it updates all search entries. If a new item ID appears or an existing item has some attributes changed, yambot sends an update through email.

## Thanks

- [mercari](https://github.com/marvinody/mercari): a wrapper around mercari jp shopping site
- [Yoku](https://github.com/kokseen1/Yoku): A minimal Yahoo! Auctions scraper.
