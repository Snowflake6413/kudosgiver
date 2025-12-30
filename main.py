import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
MODERATION_URL = os.getenv("MODERATION_URL")
MODERATION_KEY = os.getenv("MODERATION_KEY")

app=App(token=SLACK_BOT_TOKEN)

mod_client=OpenAI(
    base_url=MODERATION_URL,
    api_key=MODERATION_KEY
)


def if_txt_flagged(text):

    if not text:
        return False
    
    try:
        response = mod_client.moderations.create(input=text)
        return response.results[0].flagged
    except Exception as e:
        print(f"Moderation API error {e}")
        return True

@app.message("kudos")
def hello_fella(ack, say):
    ack()
    say("kudos to you too")

@app.command("/give-kudos")
def give_a_kudo(ack, command, client, say, respond):
    ack()
    sender_id = command["user_id"]
    txt = command["text"]



    usr_match = re.search(r"<@([A-Za-z0-9]+)\|[^>]+>", txt)

    if not usr_match:
        respond("Please mention a user to give kudos to.")
        return


    recipient_id = usr_match.group(1)
    reason = txt.replace(usr_match.group(0), "").strip()

    if not reason:
        reason = "being an awesome person!"

    if if_txt_flagged(reason):
        respond(":neocat_0_0: This message has been flagged by our moderation system. Please rewrite your message!")
        return
    
    try:
        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudo from <@{sender_id}> Here is the reason why! {reason}"
        )
        respond(f"I have sucessfully sent a kudo to <@{recipient_id}>!")
    except Exception as e:
        respond(f"Oops! Unable to send a kudo to the recipient. :( {e}")



@app.shortcut("give_kudos_shortcut")
def kudo_shortcut_modal(ack, shortcut, client):
    ack()

    trigger_id = shortcut["trigger_id"]
    recipient_id = shortcut["message"]["user"]

    client.views_open(
        trigger_id=trigger_id,
        view={
	"type": "modal",
    "callback_id" : "submit_kudos_view",
    "private_metadata" : recipient_id,
	"title": {
		"type": "plain_text",
		"text": "KudosGiver",
		"emoji": True
	},
	"submit": {
		"type": "plain_text",
		"text": "Give Kudos",
		"emoji": True
	},
	"close": {
		"type": "plain_text",
		"text": "Cancel",
		"emoji": True
	},
	"blocks": [
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*You are about to give a kudos to <@{recipient_id}>*"
			}
		},
		{
			"type": "input",
            "block_id" : "reason_block",
			"element": {
				"type": "plain_text_input",
				"action_id": "reason_action"
			},
			"label": {
				"type": "plain_text",
				"text": "Reason",
				"emoji": True
			},
			"optional": True
		}
	]
}
    )


@app.view("submit_kudos_view")
def handle_submission(ack, client, body, view):
    reason= view["state"]["values"]["reason_block"]["reason_action"]["value"]

    if not reason:
        reason = "being awesome!"

    if if_txt_flagged(reason):
        ack(response_action="errors", errors={
            "reason_block": "This message has been flagged by our moderation system. Please rewrite your message."
        })
        return
    
    ack()
    recipient_id = view["private_metadata"]
    sender_id = body["user"]["id"]

    try:
        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudo from <@{sender_id}> Here is the reason why! {reason}"
        )
    except Exception as e:
        print(f"Error sending the kudos! {e}")




# just to see how Slack captures ID
@app.message("debug")
def see_capture(message):
    user_id = message["user"]
    print(f"Received message from user: {user_id}")







if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()