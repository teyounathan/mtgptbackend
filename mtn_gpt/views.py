import json
import os
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from dotenv import load_dotenv
from openai import AzureOpenAI


conversations = {}


def bold_text(text):
    # Replace ** with <b> and </b>
    formatted_text = text.replace("**", "<b>", 1)
    while "**" in formatted_text:
        formatted_text = formatted_text.replace("**", "</b>", 1).replace("**", "<b>", 1)
    return formatted_text
 
def remove_references(response):
    # This regex will match patterns like [doc1], [doc2], etc.
    cleaned_response = re.sub(r'\[doc\d+\]', '', response)
    return cleaned_response
 

@csrf_exempt
def chat(request):
   
    load_dotenv()
    http_proxy = os.getenv('proxy')  
    https_proxy = os.getenv('proxy')  

    if http_proxy:
        os.environ['http_proxy'] = http_proxy
    if https_proxy:
        os.environ['https_proxy'] = https_proxy
       
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        message = data.get('message')  
        session = data.get('session')
  
        try:
            endpoint = os.getenv('ENDPOINT_URL')
            deployment = os.getenv('DEPLOYMENT_NAME')  
            search_endpoint = os.getenv('SEARCH_ENDPOINT')  
            search_key = os.getenv('SEARCH_KEY')  
            search_index = os.getenv('SEARCH_INDEX_NAME')  
            subscription_key = os.getenv('AZURE_OPENAI_API_KEY')  
            api_version= os.getenv('API_VERSION')
            
            # Initialize Azure OpenAI client with key-based authentication
            client = AzureOpenAI(  
                azure_endpoint=endpoint,  
                api_key=subscription_key,  
                api_version= api_version,  
            )                  
                                                                               
            personalized_message = "Y'ello! It seems I couldn't find the information you're looking for in our current dataset. Could you please try rephrasing your query or ask about a different topic? I'm here to help!"
                   
            # Prepare the chat prompt  
            chat_prompt = [
                {"role": "system", "content": "In MTN we use Y'ello instead of hello it helps rehenforce our mark and presence and consolidate our collaboration in MTN Cameroon. But say y'ello only at the begining of a conversion or when you are greeted: "},
                {"role": "system", "content": f"If the requested information is not available in the retrieved data, respond with: Y'ello! It seems I couldn't find the information you're looking for in our current dataset. Could you please try rephrasing your query or ask about a different topic? I'm here to help!"},
                {"role": "system", "content": "Your name is Morpheus. Provide information and answer questions related to MTN Cameroon. You can help answer questions related to customer experience (CEX), Human Ressource (HR) and Risk and Compliance(R&C)  . Respond as if you were an internal MTN knowledge base."},
                ]
            
            try:
                filtered_conversations = conversations[session]
                filtered_conversations.append({'role': 'user', 'content': message})
                
            except :
                conversations[session] = []
                conversations[session].append({'role': 'user', 'content': message})
                filtered_conversations = conversations[session]
                
            for conv in filtered_conversations:
                chat_prompt.append(dict(conv))
                
            
            print(chat_prompt)
            print('-'*100)
            # Generate the completion  
            completion = client.chat.completions.create(  
                model=deployment,  
                messages=chat_prompt,    
                max_tokens=1000,  
                temperature=0.5,  
                top_p=0.95,  
                frequency_penalty=0,  
                presence_penalty=0,  
                stop=None,  
                stream=False,
                extra_body={
                "data_sources": [{
                    "type": "azure_search",
                    "parameters": {
                    "endpoint": f"{search_endpoint}",
                    "index_name": f"{search_index}",
                    "semantic_configuration": "default",
                    "query_type": "semantic",
                    "fields_mapping": {},
                    "in_scope": True,
                    "role_information": f"""
                    In MTN we use Y'ello instead of hello it helps rehenforce our mark and presence and consolidate our collaboration in MTN Cameroon. But say y'ello only at the begining of a conversion or when you are greeted.
                    Your name is Morpheus. Provide information and answer questions related to MTN Cameroon. You can help answer questions related to customer experience (CEX), Human Ressource (HR) and Risk and Compliance(R&C)  . Respond as if you were an internal MTN knowledge base.                    If the requested information is not available in the retrieved data, respond with: {personalized_message}.
                    When responding make sure not to provide too much information but when you are asked or when you should do so.
                    """,
                    "filter": None,
                    "strictness": 3,
                    "top_n_documents": 5,
                    "authentication": {
                        "type": "api_key",
                        "key": f"{search_key}"
                    }
                    }
                }]
                }  
            )
            response = bold_text(remove_references(completion.choices[0].message.content))
            conversations[session].append({'role': 'assistant', 'content': response})
            
            print(conversations)
            return JsonResponse({'response': response})
 
        except Exception as e:
            print(e)
            return JsonResponse({'response': f"An unexpected error occured please try later."})