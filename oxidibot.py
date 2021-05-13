#!/bin/env python3
import sqlite3
import hashlib
from interbot import *
SCHEMA_MESSAGES = """
CREATE TABLE IF NOT EXISTS "messages" (
	"msg_id"	INTEGER NOT NULL,
	"chat_id"	INTEGER NOT NULL,
	"post_id"	INTEGER,
	PRIMARY KEY("msg_id","chat_id")
);"""
SCHEMA_POSTS = """
CREATE TABLE IF NOT EXISTS "posts" (
	"post_id"	INTEGER PRIMARY KEY AUTOINCREMENT,
	"likes"	INTEGER NOT NULL,
	"author"	INTEGER,
	"anon"	INTEGER,
	"post_at"	INTEGER
);"""
INSERT_MESSAGES = """
INSERT INTO messages(msg_id,chat_id,post_id) VALUES (?,?,?);
"""
INSERT_POSTS = """
INSERT INTO posts (likes,author,anon,post_at) VALUES (?,?,?,?);
"""
SELECT_POSTS_INBOX = """
SELECT post_id,author,anon FROM posts WHERE post_at = -1;
"""
SELECT_MESSAGES_POST = """
SELECT msg_id,chat_id FROM messages WHERE post_id = ?;
"""
DELETE_POST = """
DELETE FROM posts WHERE post_id = ?;
"""
DELETE_MESSAGES_POST = """
DELETE FROM messages WHERE post_id = ?;
"""
UPDATE_POST_PUBLISHED = """
UPDATE posts SET post_at = -2 WHERE post_id = ?;
"""


CHANNEL_ID = '@var_log_shitpost'
print(CHANNEL_ID)
def channel_post(chat_id,message_id,anon=False):
	print(chat_id)
	print(message_id)
	if anon:
		bot.copy_message(chat_id=CHANNEL_ID,from_chat_id=chat_id,message_id=message_id)
	else:
		bot.forward_message(chat_id=CHANNEL_ID,from_chat_id=chat_id,message_id=message_id)

conn = sqlite3.connect('oxidibot.db')
cursor = conn.cursor()
cursor.execute(SCHEMA_MESSAGES)
cursor.execute(SCHEMA_POSTS)
conn.commit()
#cursor.execute()

chat_state.extend_default_state({'is_admin':0,'is_suggesting':0,'post_id':-1})

help_text = """
/suggest - suggest a post to @var_log_shitpost.
/myid - send me my user id
/help - print this message
"""
@bot.message_handler(commands=['suggest'])
def suggest(message):
	if chat_state.get(message.chat.id,'is_suggesting'):
		bot.send_message(message.chat.id,'Your messages have been saved.')
		conn.commit()
		chat_state.set(message.chat.id,0,'is_suggesting')
	else:
		bot.send_message(message.chat.id,"Please, send your suggested post messages. When you're done just use /suggest command again.")
		chat_state.set(message.chat.id,1,'is_suggesting')
		cursor.execute(INSERT_POSTS,(0,message.from_user.id,0,-1))
		cursor.execute("SELECT last_insert_rowid();")
		last_post_id = cursor.fetchone()[0]
		chat_state.set(message.chat.id,last_post_id,'post_id')
@bot.message_handler(func=lambda message: bool(chat_state.get(message.chat.id,'is_suggesting')))
def post_handler(message):
	cursor.execute(INSERT_MESSAGES,(message.message_id,message.chat.id,chat_state.get(message.chat.id,'post_id')))
@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id,help_text)
@bot.message_handler(commands=['start'])
def start(message):
	bot.send_message(message.chat.id,"Heyo!")
	help(message)
@bot.message_handler(commands=['myid'])
def myid(message):
	bot.send_message(message.chat.id,str(message.from_user.id))

@bot.message_handler(commands=['auth'])
def auth(message):
	if chat_state.get(message.chat.id,'is_admin'):
		bot.send_message(message.chat.id,"Ok, I guess you're not an admin any more.")
		chat_state.set(message.chat.id,0,'is_admin')
		return
	params = message.text.split(' ')
	if len(params)<2:
		bot.send_message(message.chat.id,"You're not supposed to be here!")
		return
	provided_token = params[1].strip()
	uid = message.from_user.id
	digest = hashlib.blake2b((str(uid)+':'+API_SECRET).encode('utf-8')).hexdigest()
	print(digest)
	if digest == provided_token:
		bot.send_message(message.chat.id,"You're now an admin!")
		chat_state.set(message.chat.id,1,'is_admin')
	else:
		bot.send_message(message.chat.id,"You're not supposed to be here!")
@bot.message_handler(commands=['inbox_next'])
def show_inbox(message):
	if chat_state.get(message.chat.id,'is_admin'):
		cursor.execute(SELECT_POSTS_INBOX)
		
		post = cursor.fetchone()
		if post is None:
			bot.send_message(message.chat.id,"No new posts in inbox!")
			return
		
		for i,msg in enumerate(cursor.execute(SELECT_MESSAGES_POST,[post[0]])):
			if i ==0:
				author = bot.get_chat_member(msg[1],post[1])
				bot.send_message(message.chat.id,"New suggested post by {} {} (@{}) [{}]".format(author.user.first_name,author.user.last_name,author.user.username,"anonymous" if post[2] else "signed"))
			bot.forward_message(message.chat.id,msg[1],msg[0])
		def reject(msg):
			cursor.execute(DELETE_MESSAGES_POST,[post[0]])
			cursor.execute(DELETE_POST,[post[0]])
			conn.commit()
			bot.send_message(msg.chat.id,"Rejected post!")
		def publish(msg):
			for msg_id,chat_id in cursor.execute(SELECT_MESSAGES_POST,[post[0]]):
				channel_post(chat_id,msg_id)
			cursor.execute(UPDATE_POST_PUBLISHED,[post[0]])
			conn.commit()
			bot.send_message(msg.chat.id,"Published the post!")
		actions={
			"Post":publish,
			"Reject": reject,
			"Cancel":lambda m: bot.send_message(m.chat.id,"Cancelled review")
		}
		interbot_prompt_select(message.chat.id,"Action",actions)
	else:
		bot.send_message(message.chat.id,":(")
bot.polling()
