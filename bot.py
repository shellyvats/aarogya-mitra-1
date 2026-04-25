import aiml
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthBot:
    def __init__(self):
        self.kernel = aiml.Kernel()
        self.kernel.verbose(False)
        self._load_aiml_files()
        logger.info("HealthBot initialized successfully.")

    def _load_aiml_files(self):
        aiml_dir = os.path.join(os.path.dirname(__file__), "aiml")
        files_loaded = 0
        for filename in os.listdir(aiml_dir):
            if filename.endswith(".aiml"):
                filepath = os.path.join(aiml_dir, filename)
                self.kernel.learn(filepath)
                files_loaded += 1
                logger.info(f"Loaded: {filename}")
        logger.info(f"Total AIML files loaded: {files_loaded}")

    def respond(self, user_input):
        if not user_input or not user_input.strip():
            return "Please type a message so I can help you."
        response = self.kernel.respond(user_input.strip().upper())
        if not response or response.strip() == "":
            return (
                "I'm sorry, I didn't understand that. You can try:\n"
                "- Type SYMPTOMS to get first-aid advice\n"
                "- Type HOSPITAL IN followed by your district\n"
                "- Type SCHEMES for free government health schemes\n"
                "- Type EMERGENCY for ambulance and helpline numbers\n"
                "- Type HELP to see all options"
            )
        return response


# Quick terminal test — run this file directly to chat in terminal
if __name__ == "__main__":
    print("\n" + "="*55)
    print("   Rural Health Access Navigator — Terminal Mode")
    print("="*55)
    print("Type 'quit' to exit.\n")

    bot = HealthBot()
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "bye"):
                print("Bot: Stay healthy! Goodbye.")
                break
            if not user_input:
                continue
            reply = bot.respond(user_input)
            print(f"Bot: {reply}\n")
        except KeyboardInterrupt:
            print("\nBot: Goodbye! Stay healthy.")
            break
