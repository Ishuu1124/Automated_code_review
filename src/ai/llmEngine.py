import yaml
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

with open('config/settings.yaml') as f:
    settings = yaml.safe_load(f)

class LLMEngine:
    def __init__(
        self
    ):
        self.llm = ChatOllama(
            model=settings['MODEL']
        )
            
    def invoke(
        self,
        system_message: SystemMessage = None,
        human_message: HumanMessage = None
    ):
        self.llm_input = []
        if system_message:
            self.llm_input.append(system_message)
        if human_message:
            self.llm_input.append(human_message)
        try:
            self.response = self.llm.invoke(self.llm_input)
            if isinstance(self.response, BaseMessage):
                return self.response.content
            elif isinstance(self.response, str):
                return self.response
        except Exception as e:
            print("Something went wrong with getting the LLM response:")
            print(e)