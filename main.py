import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")


app=App(token=SLACK_BOT_TOKEN)


@app.message("kudos")
def hello_fella(ack, say):
    ack()
    say("kudos to you too")

@app.command("/give-kudos")
def give_a_kudo(ack, command, client, say):
    ack()
    sender_id = command["user_id"]
    txt = command["text"]

    usr_match = re.search(r"<@[A-Za-z0-9]+>")

    if match:
        recipient_id = usr_match.group()




# just to see how Slack captures ID
@app.message("debug")
def see_capture(message):
    user_id = message["user"]
    print(f"Received message from user: {user_id}")







if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()