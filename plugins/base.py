# plugins/base.py
# Every plugin inherits from this class
# This is the contract every plugin must follow

class Plugin:
    # Required — name of the plugin
    name = "base"
    
    # Required — description for the AI to understand when to use it
    description = "base plugin"
    
    # Required — example phrases that trigger this plugin
    triggers = []
    
    def can_handle(self, action: str, value: str) -> bool:
        """
        Return True if this plugin can handle this action.
        The AI will set action to your plugin's name.
        """
        return action.upper() == self.name.upper()
    
    def execute(self, value: str) -> tuple:
        """
        Do the thing.
        Always returns (text_result, file_path_or_None)
        """
        raise NotImplementedError
    
    def get_prompt_description(self) -> str:
        """
        Returns description for the AI system prompt.
        This tells the AI when to use your plugin.
        """
        triggers_str = ", ".join(self.triggers)
        return f"- {self.name.upper()}: {self.description} (triggers: {triggers_str})"
