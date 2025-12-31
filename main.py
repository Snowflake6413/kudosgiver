import os
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
MODERATION_URL = os.getenv("MODERATION_URL")
MODERATION_KEY = os.getenv("MODERATION_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app=App(token=SLACK_BOT_TOKEN)

mod_client=OpenAI(
    base_url=MODERATION_URL,
    api_key=MODERATION_KEY
)


def check_usr_agreement(user_id):
    try:
        response = supabase.table("user_agreements").select("user_id").eq("user_id", user_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Supabase err {e}")
        return False

def save_usr_agreement(user_id):
    try:
        supabase.table("user_agreements").insert({"user_id": user_id}).execute()
        return True
    except Exception as e:
        print(f"Unable to save : {e}")

def get_rules_block():
    return[
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": ":neocat_book: *Community Guidelines*"
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Before you send your first kudos to your buddy, please follow these rules and reminders!",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "1. Be respectful!",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "2. No inappropriate content. Moderation is in place.",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "3. Kudos's messages will be logged for safety.",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": "4. Please follow the <https://hack.af/coc|Code of Conduct> when sending kudos!"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Note on our collection policy: Your Slack ID and timestamp will be logged when you agreed to these guidelines. This information will be saved into a Supabase table. We will also collect your Slack ID, the recipient's Slack ID and the kudos reason into a seperate Supabase table. We use this information for safety purposes. If any Fire Department member asks for this information, we'll gladly hand it over to them. If you would like your data to be removed, please DM @areallyawesomeusername",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Please note that the moderation system is powered by OpenAI models. It not might be accurate and some harmful messages might slip through. If you encounter any harmful messages, please file a Shroud report or contact a FD member.",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "By agreeing to these guidelines, you allow us to collect the information listed in our collection policy and will follow the guidelines above.",
				"emoji": True
			}
		},
		{
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"text": "I agree to the above.",
						"emoji": True
					},
					"value": "agree_button",
					"action_id": "button-action"
				}
			]
		}
	]



def if_txt_flagged(text):

    if not text:
        return False
    
    try:
        response = mod_client.moderations.create(input=text)
        return response.results[0].flagged
    except Exception as e:
        print(f"Moderation API error {e}")
        return True

def kudos_data_collector(sender_id, recipient_id, reason):
# its harmless i swear :3c it just collects the recipient's and sender's slack id and the kudos reason
    try:
        supabase.table("collect_kudos").insert({
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "reason": reason
            }).execute()
        print("Capturing successful :3")
    except Exception as e:
        print(f"failed to capture :( {e}")

@app.action("button-action")
def agreement_handler(ack, respond, body):
    ack()
    user_id = body["user"]["id"]
    
    if save_usr_agreement(user_id):
        respond(text="Thank you for agreeing! You can now send kudos! :neocat_cute:", replace_original=True)
    else:
        respond(text="Error when saving the agreement. Please try again soon.", replace_original=True)

@app.message("kudos")
def hello_fella(ack, say):
    ack()
    say("kudos to you too")

@app.command("/give-kudos")
def give_a_kudo(ack, command, client, say, respond):
    ack()
    sender_id = command["user_id"]
    if not check_usr_agreement(sender_id):
        respond(
            text="It looks like you havent agreed to our guidelines, please read it first!",
            blocks=get_rules_block()
        )
        return
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
        kudos_data_collector(sender_id, recipient_id, reason)
        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudos from <@{sender_id}> Here is the reason why! {reason}"
        )
        respond(f"I have sucessfully sent a kudos to <@{recipient_id}>!")
    except Exception as e:
        respond(f"Oops! Unable to send a kudos to the recipient. :( {e}")

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
        kudos_data_collector(sender_id, recipient_id, reason)
        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudos from <@{sender_id}> Here is the reason why! {reason}"
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