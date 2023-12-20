############# BOT IMPORTS ###########################
import os
#from slack_sdk.errors import SlackApiError
#import slack
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
############# AI IMPORTS ###########################
import pickle
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chains.question_answering import load_qa_chain
from langchain.chat_models import ChatOpenAI
import time
import json

############# SETTINGS ###########################

""" SLACK_TOKEN_= "xoxb-6102082131061-6112088037186-7O6HDbh12IymTGHqsJxTDLlq"
CHANNEL_ID_ = "C0637BSF5A7"
BOT_ID = 'U063A2L135G'
os.environ["OPENAI_API_KEY"] = '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'  """

from dotenv import load_dotenv
import os
load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SLACK_TOKEN = os.getenv("SLACK_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
BOT_ID = os.getenv("BOT_ID")

client = WebClient(token= SLACK_TOKEN)  # Initialize a Web API client


############# LISTEN TO MESSAGES IN A CHANNEL ###########################
def listen_to_channel(channel_id):
    # Get the last message in the channel
    result = client.conversations_history(channel=channel_id, limit=1)
    last_message = result["messages"][0]["text"]
    user = result["messages"][0]["user"]
    message_ts = result["messages"][0]["ts"]

    # Check if the message is part of a thread
    if 'thread_ts' in result["messages"][0]:
        thread_ts = result["messages"][0]["thread_ts"]
        return last_message, user, message_ts, thread_ts, result

    return last_message, user, message_ts, None, result 

def listen_to_thread(channel_id, thread_ts):
    # Get the last message in the specified thread
    result = client.conversations_replies(channel=channel_id, ts=thread_ts, limit=1)
    
    # Check if there are replies in the thread
    if result["messages"]:
        last_message = result["messages"][0]["text"]
        user = result["messages"][0]["user"]
        message_ts = result["messages"][0]["ts"]
        return last_message, user, message_ts, result
    
    # If there are no replies, return None
    return None, None, None, result



def get_last_message_in_thread(channel_id, parent_ts):
    result = client.conversations_replies(channel=channel_id, ts=parent_ts)
    replies = result.get("messages", [])

    # Sort replies by timestamp in descending order
    sorted_replies = sorted(replies, key=lambda x: float(x.get("ts", 0)), reverse=True)

    # Get the information of the latest reply
    last_reply = sorted_replies[0]
    last_message = last_reply.get("text", "")
    user = last_reply.get("user", "")
    message_ts = last_reply.get("ts", "")

    return last_message, user, message_ts, result

############## LANGCHAIN WEB AGENT ###################################


from langchain.chat_models import ChatOpenAI
from langchain.agents import AgentType, Tool, initialize_agent
from langchain.agents import AgentType, initialize_agent, load_tools
from langchain.document_loaders import DirectoryLoader


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# in the Google Cloud Console > Library > enable Custom Search API 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
# in the Google Programmable Search Engine
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID_WEB")

llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, model_name='gpt-4', temperature=0.0)
tool = load_tools(["google-search"], llm=llm, google_api_key=GOOGLE_API_KEY , google_cse_id=GOOGLE_CSE_ID)
agent = initialize_agent(tool, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, return_intermediate_steps=False)

# query = "what is the software that controls the Planktoscope?" 
# print(agent(query)['output'])


############# CREATE A THREAD & SEND MESSAGE ###########################
def send_message(channel_id, message, message_ts):
    try:
        result = client.chat_postMessage(channel=channel_id, text=message, thread_ts=message_ts)
    except SlackApiError as e:
        print(f"Error: {e.response['error']}")

# Replace 'your_file.json' with the path to your JSON file
file_path = 'data.json'

# Open the JSON file and load the data
with open(file_path, 'r') as file:
    data = json.load(file)
    
if __name__ == "__main__":
    running = True
    #active_threads = set()  # Set to keep track of active threads
    #fichier=open("/homes/m22dahba/Bureau/BOT/fetch.txt","a")
    current_message, user, message_ts, thread_ts, result = listen_to_channel(CHANNEL_ID)
    while running:
        
        try:
            current_message, user, message_ts, thread_ts, result = listen_to_channel(CHANNEL_ID)
            last_message, user, last_message_ts, result = get_last_message_in_thread(CHANNEL_ID, message_ts) 
          
            # Process new message
            if user != BOT_ID:
                if result['messages'][0]['blocks'][0]['elements'][0]['elements'][0]['user_id'] == BOT_ID :
                    print(user , current_message, last_message)

                    send_message(CHANNEL_ID, f"Hi <@{user}>! :robot_face: \n I'm working on your request...", message_ts)
                    # If the message is part of a thread
                    with open('data.json', 'r') as file:
                        data = json.load(file)
                    data[message_ts]=current_message
                    with open('data.json', 'w') as file:
                        json.dump(data, file, indent=0)

                    
                    query = last_message
                    send_message(CHANNEL_ID, agent(query)['output'], message_ts)
                    user = BOT_ID

          

            # Check each active thread for new messages
            for active_thread in data.keys():
                last_message, thread_user, last_message_ts, result = get_last_message_in_thread(CHANNEL_ID, active_thread)
                if thread_user != BOT_ID:
                    if result['messages'][0]['blocks'][0]['elements'][0]['elements'][0]['user_id'] == BOT_ID :
                        send_message(CHANNEL_ID, f"Thanks for your request <@{thread_user}>! \n I'm on it...", active_thread)
                        # Process the message in the thread
                        # Example: send a response
                        print(thread_user , current_message, last_message)
                        query = last_message
                        send_message(CHANNEL_ID, agent(query)['output'], active_thread)

            # Optional: Clean up old threads from active_threads set
            # Example: Remove threads older than 1 hour
            # active_threads = {t for t in active_threads if time.time() - t < 3600}

            time.sleep(1)  # Sleep to avoid hitting rate limits

        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)  # Sleep longer if an error occurs

 