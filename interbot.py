import telebot
class ChatState:
    
    def __init__(self,default_state={}):
        self.state = {}
        self.default_state = default_state
        self.generic_message_handlers = {}

    def extend_default_state(self,state):
        self.default_state.update(state)
    def get(self,chat_id,user_id,prop=None):#FIXME: Make state dependent on the sender
        if (chat_id,user_id) in self.state:
            if prop is None: 
                return self.state[chat_id,user_id]
            else:
                return self.state[chat_id,user_id][prop]
        else:
            if prop is None: 
                return self.default_state
            else:
                return self.default_state[prop]
    def set(self,chat_id,user_id,value,prop=None):
        if (chat_id,user_id) in self.state:
            if prop is None: 
                self.state[chat_id,user_id].update(value)
            else:
                self.state[chat_id,user_id][prop] = value
        else:
            if prop is None: 
                self.state[chat_id,user_id] = self.default_state.copy()
                self.state[chat_id,user_id].update(value)
            else:
                self.state[chat_id,user_id] = self.default_state.copy()
                self.state[chat_id,user_id][prop] = value
    def push_handler(self,chat_id,user_id,handler):
        if (chat_id,user_id) in self.generic_message_handlers:
            self.generic_message_handlers[chat_id,user_id].append(handler)
        else:
            self.generic_message_handlers[chat_id,user_id] = [handler]
    def has_handler(self,chat_id,user_id):
        return (chat_id,user_id) in self.generic_message_handlers and len(self.generic_message_handlers[chat_id,user_id])>0
    def pop_handler(self,chat_id,user_id):
        if (chat_id,user_id) in self.generic_message_handlers:
            if len(self.generic_message_handlers[chat_id,user_id])>0:
                h = self.generic_message_handlers[chat_id,user_id].pop()
                if len(self.generic_message_handlers[chat_id,user_id])==0:
                    del self.generic_message_handlers[chat_id,user_id]
                return h
        return lambda m: None
chat_state = ChatState()

API_SECRET='133714888f00ba17'
try:
    with open('secret.txt') as s:
        API_SECRET = s.read()
        bot = telebot.TeleBot(API_SECRET,threaded=False)
    
except IOError as e :
    print("Can't open secret.txt:",e)
    exit(1)
@bot.message_handler(func=lambda m: chat_state.has_handler(m.chat.id,m.from_user.id))
def generic_message_handler(message):
    chat_state.pop_handler(message.chat.id,message.from_user.id)(message)
def interbot_prompt_select(chat_id,user_id,prompt,handlers={}):
    #handlers: {'reply 1':handler1(message)}

    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for reply in handlers:
        markup.add(telebot.types.KeyboardButton(reply))
    def selection_handler(message):
        if message.text in handlers: 
            markup = telebot.types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id,"OK",reply_markup=markup)
            handlers[message.text](message)
           
        else:
            chat_state.push_handler(chat_id,user_id,selection_handler)
    bot.send_message(chat_id,prompt+"?",reply_markup=markup)
    chat_state.push_handler(chat_id,user_id,selection_handler)
    