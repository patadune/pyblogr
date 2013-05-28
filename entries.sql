CREATE VIRTUAL TABLE entries USING fts3(type, title, content, datetime, media)
