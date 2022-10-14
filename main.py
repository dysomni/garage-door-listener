from dotenv import load_dotenv

load_dotenv()

from garage_door_listener.listener import start

print('now starting listener')
start()
print('listener closing')
