import emoji, hashlib, operator, datetime, logging
import redis as redis
from typing import Any ##, String


from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery, ContentType, ParseMode
from aiogram import types
from aiogram.dispatcher.filters.state import StatesGroup, State

from aiogram_dialog import Dialog, DialogManager, DialogRegistry, Window, ChatEvent, StartMode##, DialogProtocol
from aiogram_dialog.manager.manager import ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Select, Group, ScrollingGroup, SwitchTo, Row, Column, Back, Radio, Start
from aiogram_dialog.widgets.text import Const, Format, Multi, Progress, Case
from aiogram_dialog.context.context import Context

from tgbot.models.role import UserRole

from tgbot.services.repository import Repo

logger = logging.getLogger(__name__)

r = redis.Redis(host='localhost', port=6379, username='default',  password='*****')

script_json = [{"name":"categories","list":
    [
    {
    "name":'Категория 1', "list":
        [
        {"name":'Категория 1.1', "list":
            [
            {"name":'Категория 1.1.1',
            "list":[]
            },
            {"name":'Категория 1.1.2',
            "list":[]
            },
            ]
        },
        {"name":'Категория 1.2', "list":[]
        },
        {"name":'Категория 1.3', "list":[]
        },
        ]
    },
    {
    "name":'Категория 2', "list":
        [
        {"name":'Категория 2.1', "list":
            [
            {"name":'Категория 2.1.1', "list":[]
            },
            {"name":'Категория 2.1.2', "list":[]
            },
            ]
        },
        {"name":'Категория 2.2', "list":[]
        },
        {"name":'Категория 2.3', "list":[]
        }
        ]
    }
    ]
    }
]

################# main dialog ########
class DialogSG(StatesGroup):
    mainMenu = State()
    cats = State()
    ask_operator = State()

async def get_data_cats(dialog_manager: DialogManager, aiogd_context: Context, **kwargs): 
    cur_cat_list = list(filter(lambda item: item['name'] == "categories", script_json))
    cur_cat=cur_cat_list[0]

    cat_list=[]
    i=0
    for cat in cur_cat["list"]:
        # logger.warning('cat='+str(cat))
        cat_list.append((str(i), cat["name"]))
        i=i+1
    
    logger.warning('get_data_categories..cat_list:'+str(cat_list))
    return {
        "can_ask_operator": False,
        "cat_list":cat_list,
    }

async def on_select_cat(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    cur_user_first_name= manager.current_context().start_data.get("cur_user_first_name", None)
    cur_user_id = manager.current_context().start_data.get("cur_user_id", None)

    await manager.start(DialogSG.mainMenu, {"cur_user_first_name": cur_user_first_name, "cur_user_id": cur_user_id, "parent_cat":"categories", "cat_id":item_id}, mode=StartMode.NEW_STACK)


dialog = Dialog(
    Window(
        Format('''Выберите, что Вас интересует:'''),
        ScrollingGroup(
            Select(
                Format('{item[1]}'),  
                id="s_cats", 
                item_id_getter=operator.itemgetter(0),  ## each item is a tuple with id on a first position
                items="cat_list",  
                on_click=on_select_cat,##this is only for Select
                # on_state_changed = ideas_on_state_changed,##this is only for MultiSelect
            ),
            width=1,## в ScrollingGroup без этого параметра тоже ошибка exception=ZeroDivisionError
            height=10,
            id="sg_cats"
        ),
        Row(
            SwitchTo(Const("Позвать оператора"), when="can_ask_operator", id="btn_ask_operator", state=DialogSG.ask_operator),
        ),
        getter=get_data_cats,
        state=DialogSG.cats,
    )
)

# @dp.message_handler(commands=["start"])
async def user_start(m: Message, dialog_manager: DialogManager):
    my_debug_string=''
    # logger.warning('m.text='+str(m.text))
    start_hash = m.text.replace('/start','').strip() ## extract hash from the start command
    # logger.warning('start_hash='+str(start_hash))
    global r
    start_params = None
    start_params_s = ''
    if start_hash!='':
        start_params = r.get(start_hash) ##replace hash with cashed start params 
        if start_params:
            start_params_s=start_params.decode() if start_params!='' else ''
        else:
            start_params_s = start_hash 
    else:
        start_params =''
    
    start_params_list=start_params_s.split('_')
    # start_params_list = list(start_params_s.strip().replace('_',','),',')

    logger.warning('user_start: '+str(m.from_user.username)) ##+' user_id='+str(m.from_user.id)
    await dialog_manager.start(DialogSG.cats, {"cur_user_first_name": m.from_user.first_name, "cur_user_id": m.from_user.id, "parent_cat":None, "cat_id":None}, mode=StartMode.RESET_STACK)
            
async def user_cmd(m: Message, dialog_manager: DialogManager):
    cmd_item = m.text.replace('/OOOOOOOO','').strip() ## extract hash from the start command
    logger.warning('cmd_item='+str(cmd_item))
    

def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
    dp.register_message_handler(user_cmd, commands=["OOOOOOOO1","OOOOOOOO2","OOOOOOOO3","OOOOOOOO4"], state="*")
    registry = DialogRegistry(dp)
    #### register default handler, which resets stack and start dialogs on /start command
    ### registry.register_start_handler(DialogSG.mainMenu)
    registry.register(input_dialog)
    registry.register(dialog)

