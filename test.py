# from pymilvus import connections
# connections.connect()
# connections.get_connection().is_connected 

from ibm_watsonx_ai.foundation_models import Embeddings, get_embedding_model_specs
# from ibm_watsonx_ai.client import 
from ibm_watsonx_ai.foundation_models.utils.enums import EmbeddingTypes


data = {
    'id': 'chatcmpl-9eb54ed142b9291168a2dccc49d0c202',
    'object': 'chat.completion',
    'model_id': 'ibm/granite-3-3-8b-instruct',
    'model': 'ibm/granite-3-3-8b-instruct',
    'choices': [{
        'index': 0,
        'message':{
            'role': 'assistant',
            'content': "Hello! How can I assist you today?\n\nLet me know if you have any questions or need information on a specific topic. I'm here to help with a wide range of inquiries, from general knowledge to advice on various subjects."
        },
        'finish_reason': 'stop'
    }],
    'created': 1748265824,
    'model_version': '3.3.0',
    'created_at': '2025-05-26T13: 23: 44.848Z',
    'usage': {
        'completion_tokens': 51,
        'prompt_tokens': 59,
        'total_tokens': 110
    },
    'system': {
        'warnings': [{
            'message': "The value of 'max_tokens' for this model was set to value 1024",
            'id': 'unspecified_max_token',
            'additional_properties': {
                'limit': 0,
                'new_value': 1024,
                'parameter': 'max_tokens',
                'value': 0
            }
        }]
    }
}