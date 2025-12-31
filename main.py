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

def fetch_kudos_stats(user_id):
    try:
        sent_response = supabase.table("collect_kudos").select("id").eq("sender_id", user_id).execute()
        sent_count = len(sent_response.data)
    
        recieved_response = supabase.table("collect_kudos").select("id").eq("recipient_id", user_id).execute()
        recieved_count = len(recieved_response.data)

        return sent_count, recieved_count
    except Exception as e:
        print(f"Error when fetching stats!")
        return 0,0
    

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
    
def add_to_opt_out_table(user_id):
    try:
        supabase.table("kudos_opt_out").insert({"user_id": user_id}).execute()

        supabase.table("user_agreements").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Unable to add to opt-out list: {e}")
        return False
    

def remove_from_opt_out_table(user_id):
    try:
        supabase.table("kudos_opt_out").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        print(f"Unable to remove from opt-out list: {e}")
        return False

def check_if_opt_out(user_id):
    try:
        response = supabase.table("kudos_opt_out").select("user_id").eq("user_id", user_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"Unable to check if user is opt-out. {e}")

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

@app.command("/opt-out")
def opt_out_cmd(ack, command, respond):
    ack()
    user_id = command["user_id"]

    if check_if_opt_out(user_id):
        respond(text="You have already opted out!", replace_original=False)
        return
    
    if add_to_opt_out_table(user_id):
        respond(text="You have opt-out. You will no longer recieve kudos or send kudos to a user. :neocat_sad_reach:", replace_original=False)
    else:
        respond("Error when trying to opt-out. Please try again.")

@app.command("/opt-in")
def opt_in_cmd(ack, respond, command):
    ack()
    user_id = command["user_id"]

    if not check_if_opt_out(user_id):
        respond(text=":neocat_cute: You are already opted in! ", replace_original=False)
        return
    
    if remove_from_opt_out_table(user_id):
        respond(
            text=":neocat_box: Welcome back! You've successfully opted in. To start sending kudos again, please review and agree to the guidelines below!",
            blocks=get_rules_block()
        )
    else:
        respond(text="Oops! Something went wrong while trying to opt you back in. Please try again later. :neocat_sad_reach:")

@app.command("/help")
def help_cmd(ack, respond):
    ack()

    help_blocks = [
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "KudosGiver Help :neocat_book: ",
				"emoji": True
			}
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "/give-kudos @User Reason",
				"emoji": True
			}
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "plain_text",
					"text": "Give kudos to a friend!",
					"emoji": True
				}
			]
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "/opt-out",
				"emoji": True
			}
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "plain_text",
					"text": "Opt-out of the kudos system. :neocat_sad:",
					"emoji": True
				}
			]
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "/opt-in",
				"emoji": True
			}
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "plain_text",
					"text": "Opt-in of the kudos system.",
					"emoji": True
				}
			]
		},
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "/my-kudos",
				"emoji": True
			}
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "plain_text",
					"text": "Check how many kudos you recieved and sent!",
					"emoji": True
				}
			]
		}
	]

    respond(blocks=help_blocks)

    
@app.command("/my-kudos")
def kudos_cmd(ack, command, respond):
    ack()
    user_id = command["user_id"]
    
    if check_if_opt_out:
        respond(text="You have opted out and your unable to see your stats. Please opt-in to see your stats! :neocat_blank:")
        return
    
    sent_count, recieved_count = fetch_kudos_stats(user_id)

    stat_blocks = [
        
		{
			"type": "section",
			"text": {
				"type": "plain_text",
				"text": "Your Kudos Stats! :neocat_heart:",
				"emoji": True
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*Kudos Sent:*\n{sent_count}"
			}
		},
		{
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": f"*Kudos Received:*\n{received_count}"
			}
		},
		{
			"type": "divider"
		},
		{
			"type": "context",
			"elements": [
				{
					"type": "plain_text",
					"text": "Keep on sending kudos!",
					"emoji": True
				}
			]
		}
	]
    respond(blocks=stat_blocks)

@app.message("kudos")
def hello_fella(ack, say):
    ack()
    say("kudos to you too")

@app.command("/give-kudos")
def give_a_kudo(ack, command, client, say, respond):
    ack()
    sender_id = command["user_id"]

    
    if check_if_opt_out(sender_id):
        respond(text="You have opted out from this kudos system. You are unable to send kudos. To opt-in again, run /opt-in. :neocat_baa:", replace_original=False)
        return

    if not check_usr_agreement(sender_id):
        respond(
            text="It looks like you haven't agreed to our guidelines, please read it first!",
            blocks=get_rules_block()
        )
        return
    txt = command["text"]



    usr_match = re.search(r"<@([A-Za-z0-9]+)\|[^>]+>", txt)

    if not usr_match:
            respond("Please mention a user to give kudos to.")
            return
    
    recipient_id = usr_match.group(1)


    if sender_id == recipient_id:
        respond(text='You cannot give kudos to yourself. :neocat_laugh:')
        return

    if check_if_opt_out(recipient_id):
        respond(f"Oops! <@{recipient_id}> has opted out. You cannot send kudos to this user. :neocat_sad_reach:")
        return

    reason = txt.replace(usr_match.group(0), "").strip()

    if not reason:
        reason = "being an awesome person!"

    if if_txt_flagged(reason):
        respond(":neocat_0_0: This message has been flagged by our moderation system. Please rewrite your message!")
        return
    
    try:
        kudos_data_collector(sender_id, recipient_id, reason)

        msg_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":neocat_heart: *You received a kudos from <@{sender_id}>*\n\n> {reason}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Return the favor :neocat_hug:",
                        "emoji": True
                    },
                    "value": sender_id,
                    "action_id": "return_kudos"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Opt-out :neocat_sad_reach: ",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": "opt_out_action",
                    "action_id": "opt_out",
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Opt-out?"
                        },
                        "text": {
                            "type": "plain_text",
                            "text": "Are you sure you want to opt-out? You won't be able to send or recieve kudos anymore."
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Yes, opt-out"
                        },
                        "deny": {
                            "type": "plain_text",
                            "text": "Cancel"
                        }
                    }
                }
            ]
        }
    ]

        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudos from <@{sender_id}> Here is the reason why! {reason}",
            blocks=msg_blocks
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
    sender_id = body["user"]["id"]

    if not check_usr_agreement(sender_id):
        ack(response_action="errors", errors={
            "reason_block": "You haven't agreed to our guidelines! To use this service, run the /opt-in command."
        })
        return

    if check_if_opt_out(sender_id):
        ack(response_action="errors", errors={
            "reason_block": "You have opted out and unable to send kudos. To opt-in, run the /opt-in command."
        })
        return
    
    reason= view["state"]["values"]["reason_block"]["reason_action"]["value"]

    if not reason:
        reason = "being awesome!"

    if if_txt_flagged(reason):
        ack(response_action="errors", errors={
            "reason_block": "This message has been flagged by our moderation system. Please rewrite your message."
        })
        return
    
    recipient_id = view["private_metadata"]
    


    if check_if_opt_out(recipient_id):
        ack(response_action="errors", errors={
            "reason_block": f"Oops! <@{recipient_id} has opted out. You cannot send kudos to this user. :neocat_sad_reach:"
        })
        return
    ack()

    sender_id = body["user"]["id"]

    try:
        kudos_data_collector(sender_id, recipient_id, reason)
        msg_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":neocat_heart: *You received kudos back from <@{sender_id}>*\n\n> {reason}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Return the favor (again) :neocat_hug:",
                        "emoji": True
                    },
                    "value": sender_id,
                    "action_id": "return_kudos"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Opt-out :neocat_sad_reach: ",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": "opt_out_action",
                    "action_id": "opt_out",
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Opt-out?"
                        },
                        "text": {
                            "type": "plain_text",
                            "text": "Are you sure you want to opt-out? You won't be able to send or recieve kudos anymore."
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Yes, opt-out"
                        },
                        "deny": {
                            "type": "plain_text",
                            "text": "Cancel"
                        }
                    }
                }
            ]
        }
    ]
        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudos from <@{sender_id}> Here is the reason why! {reason}",
            blocks=msg_blocks
        )
    except Exception as e:
        print(f"Error sending the kudos! {e}")

@app.view("return_kudos_submission")
def return_submission_handler(ack, body, client, view):
    sender_id = body["user"]["id"]
    recipient_id = view["private_metadata"]

    if sender_id == recipient_id:
        ack(response_action="errors", errors={
            "reason_block": "You cannot give kudos to yourself!"
            })
        return

    if not check_usr_agreement(sender_id):
        ack(response_action="errors", errors={
            "reason_block": "You haven't agreed to our guidelines! To use this service, run the /opt-in command."
            })
        return


    if check_if_opt_out(sender_id):
            ack(response_action="errors", errors={
                "reason_block": "You have opted out and unable to send kudos. To opt-in, run the /opt-in command."
            })
            return
    
    reason= view["state"]["values"]["return_reason_block"]["reason_action"]["value"]

    

    if not reason:
        reason = "returning the favor!"

    if if_txt_flagged(reason):
        ack(response_action="errors", errors={
            "return_reason_block": "This message has been flagged by our moderation system. Please rewrite your message."
        })
        return
    
    ack()
    recipient_id = view["private_metadata"]

    if check_if_opt_out(recipient_id):
        ack(response_action="errors", errors={
            "reason_block": f"Oops! <@{recipient_id} has opted out. You cannot send kudos to this user. :neocat_sad_reach:"
        })
        return

    

    try:
        kudos_data_collector(sender_id, recipient_id, reason)
        msg_blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":neocat_heart: *You received a kudos from <@{sender_id}>*\n\n> {reason}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Return the favor :neocat_hug:",
                        "emoji": True
                    },
                    "value": sender_id,
                    "action_id": "return_kudos"
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Opt-out :neocat_sad_reach: ",
                        "emoji": True
                    },
                    "style": "danger",
                    "value": "opt_out_action",
                    "action_id": "opt_out",
                    "confirm": {
                        "title": {
                            "type": "plain_text",
                            "text": "Opt-out?"
                        },
                        "text": {
                            "type": "plain_text",
                            "text": "Are you sure you want to opt-out? You won't be able to send or recieve kudos anymore."
                        },
                        "confirm": {
                            "type": "plain_text",
                            "text": "Yes, opt-out"
                        },
                        "deny": {
                            "type": "plain_text",
                            "text": "Cancel"
                        }
                    }
                }
            ]
        }
    ]
        client.chat_postMessage(
            channel=recipient_id,
            text=f":neocat_heart: You recieved a kudos from <@{sender_id}> Here is the reason why! {reason}",
            blocks=msg_blocks
        )
    except Exception as e:
        print(f"Error sending the kudos! {e}")


@app.action("return_kudos")
def return_kudos_handler(ack, body, client):
    ack()
    trigger_id = body["trigger_id"]
    origin_sender = body["actions"][0]["value"]

    client.views_open(
        trigger_id=trigger_id,
        view={
    "type": "modal",
    "callback_id": "return_kudos_submission",
    "private_metadata": origin_sender,
    "title": {
        "type": "plain_text",
        "text": "Return Kudos",
        "emoji": True
    },
    "submit": {
        "type": "plain_text",
        "text": "Send Back",
        "emoji": True
    },
    "close": {
        "type": "plain_text",
        "text": "Cancel",
        "emoji": True
    },
    "blocks": [
        {
            "type": "input",
            "block_id": "return_reason_block",
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


@app.action("opt_out")
def opt_out_handler(ack, body, respond):
    ack()
    user_id = body["user"]["id"]


    try:
        if add_to_opt_out_table(user_id):
            respond(
            text="You have opt-out. You will no longer recieve kudos or send kudos to a user.",
            replace_original=False
    )
        else:
            respond(
            text="You are already opted out.",
            replace_original=False
    )
    except Exception as e:
        respond(f"Unable to opt-out :( {e}")




if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()